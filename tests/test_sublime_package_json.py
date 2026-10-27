"""
Tests for `sublime-package.json`, the file that teaches Sublime Text what this plugin's settings
mean.

It is hand-written JSON with comments, which nothing in this repo validates, and it names the
resource a package ships its rules in -- two names that have to agree with the code exactly, or
package authors get a red squiggle on a valid file (or none on an invalid one).
"""

import json
from pathlib import Path
from typing import Any

import pytest

import plugin.package_rules as package_rules
from plugin.package_rules import RULES_RESOURCE_NAME
from plugin.package_rules import SPEC_VERSION

_SCHEMA_FILE = Path(__file__).parent.parent / "sublime-package.json"


def load_schema_file() -> dict[str, Any]:
    """Parse the file the way Sublime Text does: JSON with `//` comments."""
    raw = _SCHEMA_FILE.read_text(encoding="utf-8")

    out: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(raw):
        char = raw[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif raw.startswith("//", index):
            while index < len(raw) and raw[index] != "\n":
                index += 1
            continue
        else:
            out.append(char)
        index += 1
    return json.loads("".join(out))


@pytest.fixture(scope="module")
def contributions() -> list[dict[str, Any]]:
    return load_schema_file()["contributions"]["settings"]


@pytest.fixture(scope="module")
def definitions(contributions) -> dict[str, Any]:
    return contributions[0]["schema"]["definitions"]


def find_contribution(contributions: list[dict[str, Any]], file_pattern: str) -> dict[str, Any] | None:
    return next((c for c in contributions if file_pattern in c["file_patterns"]), None)


def deref(contributions, ref: str) -> dict[str, Any]:
    """Follow a `sublime://settings/...#/definitions/name` reference."""
    return contributions[0]["schema"]["definitions"][ref.rpartition("/definitions/")[2]]


def rules_file_schema(contributions) -> dict[str, Any]:
    """The definition the rules file's contribution points at (the contribution itself is a `$ref`)."""
    contribution = find_contribution(contributions, f"/{RULES_RESOURCE_NAME}")
    assert contribution is not None, f"no schema contribution for {RULES_RESOURCE_NAME}"
    return deref(contributions, contribution["schema"]["$ref"])


class TestSchemaFile:
    def test_parses(self, contributions):
        assert contributions

    def test_rules_file_has_a_schema(self, contributions):
        """Without this, a package author gets no completion or validation for their rules file --
        and a typo there reaches users instead of showing up in their editor."""
        assert rules_file_schema(contributions)


class TestVersionDispatch:
    """`spec_version` exists because the envelope -- the keys around `rules` -- changes between
    versions. A schema that lists every key in one flat definition would lock every version to the
    newest envelope and then flag an older, valid file, which is the opposite of its job."""

    def test_the_schema_dispatches_on_spec_version(self, contributions):
        schema = rules_file_schema(contributions)

        assert "oneOf" in schema, "versions must be separate branches, picked by spec_version"

    def test_every_version_the_parser_implements_has_a_branch(self, contributions):
        branches = {
            deref(contributions, branch["$ref"])["properties"]["spec_version"]["const"]
            for branch in rules_file_schema(contributions)["oneOf"]
        }

        assert branches == set(package_rules._ENVELOPE_PARSERS), (
            "a version the parser implements but the schema doesn't leaves valid files flagged;"
            " a version the schema describes but the parser doesn't offers authors a file that"
            " will be rejected at runtime"
        )

    def test_the_newest_version_is_the_one_the_plugin_reports(self, contributions):
        assert SPEC_VERSION in {
            deref(contributions, b["$ref"])["properties"]["spec_version"]["const"]
            for b in rules_file_schema(contributions)["oneOf"]
        }


class TestV1Schema:
    def test_describes_what_the_parser_accepts(self, contributions):
        envelope = deref(contributions, "sublime://settings/AutoSetSyntax#/definitions/package_syntax_rules_v1")

        # keep in step with `_EnvelopeV1`, which rejects any other top-level key
        assert set(envelope["properties"]) == {"spec_version", "rules", "$schema"}
        assert envelope["additionalProperties"] is False
        assert set(envelope["required"]) == {"spec_version", "rules"}

    def test_rules_mean_the_same_as_in_the_settings(self, contributions):
        """`rules` must mean exactly what `user_syntax_rules` means, or an author writes a rule
        that validates in their editor and is then dropped at runtime."""
        envelope = deref(contributions, "sublime://settings/AutoSetSyntax#/definitions/package_syntax_rules_v1")

        assert envelope["properties"]["rules"]["$ref"] == (
            contributions[0]["schema"]["$id"] + "#/definitions/syntax_rule_collection"
        )
