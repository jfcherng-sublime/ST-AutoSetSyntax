"""
Tests for `sublime-package.json`, the file that teaches Sublime Text what this plugin's settings
mean.

It is hand-written JSON with comments, which nothing in this repo validates, and it names the
resource a package ships its rules in -- names that have to agree with the code exactly, or package
authors get a red squiggle on a valid file (or none on an invalid one).
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

import plugin.package_rules as package_rules
from plugin.package_rules import SPEC_VERSION
from plugin.package_rules import rules_resource_name

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


def deref(contributions, ref: str) -> dict[str, Any]:
    """Follow a `sublime://settings/...#/definitions/name` reference."""
    return contributions[0]["schema"]["definitions"][ref.rpartition("/definitions/")[2]]


def rules_contributions(contributions) -> list[dict[str, Any]]:
    """Every contribution for a rules file a package may ship, whatever its version."""
    pattern = re.compile(r"/AutoSetSyntax\.rules\.v\d+\.sublime-settings$")
    return [c for c in contributions if any(pattern.search(p) for p in c["file_patterns"])]


class TestSchemaFile:
    def test_parses(self, contributions):
        assert contributions


class TestVersionedContributions:
    """The format version is in the file name, so the dispatch is one `file_patterns` entry per
    version. That keeps each version's schema on its own and lets a new version be added by
    appending, rather than by editing what an existing version already means."""

    def test_every_implemented_version_has_an_entry(self, contributions):
        patterns = {p for c in rules_contributions(contributions) for p in c["file_patterns"]}

        assert patterns == {f"/{rules_resource_name(v)}" for v in package_rules._ENVELOPE_PARSERS}, (
            "a version the parser implements but the schema doesn't leaves valid files flagged;"
            " a version the schema describes but the parser doesn't offers authors a file that"
            " validates and is then rejected at runtime"
        )

    def test_no_dispatcher_definition(self, definitions):
        """A `oneOf` over versions would collapse every error to "matches no branch", losing the
        key that's actually wrong -- the one thing this schema exists to point at."""
        for name, definition in definitions.items():
            if not name.startswith("package_syntax_rules"):
                continue
            assert "oneOf" not in definition, f"{name} dispatches with oneOf; use file names instead"

    def test_the_version_is_not_also_a_field(self, definitions):
        """Two authorities for one fact can disagree; the file name is the only one."""
        for name, definition in definitions.items():
            if name.startswith("package_syntax_rules"):
                assert "spec_version" not in definition.get("properties", {}), name


class TestV1Schema:
    def test_describes_what_the_parser_accepts(self, contributions, definitions):
        envelope = deref(contributions, "sublime://settings/AutoSetSyntax#/definitions/package_syntax_rules_v1")

        # keep in step with `_EnvelopeV1`, which rejects any other top-level key
        assert set(envelope["properties"]) == {"rules", "$schema"}
        assert envelope["additionalProperties"] is False
        assert envelope["required"] == ["rules"]

    def test_rules_mean_the_same_as_in_the_settings(self, contributions):
        """A rule must mean exactly what it means in `user_syntax_rules`, or an author writes a
        rule that validates in their editor and is then dropped at runtime."""
        envelope = deref(contributions, "sublime://settings/AutoSetSyntax#/definitions/package_syntax_rules_v1")

        assert envelope["properties"]["rules"]["$ref"] == (
            contributions[0]["schema"]["$id"] + "#/definitions/syntax_rule_collection"
        )

    def test_declares_itself_an_object(self, contributions):
        """Without `type: object`, `properties`/`required`/`additionalProperties` are silently
        skipped for a non-object instance -- the branch would accept anything."""
        envelope = deref(contributions, "sublime://settings/AutoSetSyntax#/definitions/package_syntax_rules_v1")

        assert envelope["type"] == "object"


def test_spec_version_matches_the_definitions(contributions):
    assert max(package_rules._ENVELOPE_PARSERS) == SPEC_VERSION
