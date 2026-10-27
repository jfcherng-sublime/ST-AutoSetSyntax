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

from plugin.package_rules import RULES_RESOURCE_NAME

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


def find_contribution(contributions: list[dict[str, Any]], file_pattern: str) -> dict[str, Any] | None:
    return next((c for c in contributions if file_pattern in c["file_patterns"]), None)


class TestSchemaFile:
    def test_parses(self, contributions):
        assert contributions

    def test_rules_file_has_a_schema(self, contributions):
        """Without this, a package author gets no completion or validation for their rules file --
        and a typo there reaches users instead of showing up in their editor."""
        contribution = find_contribution(contributions, f"/{RULES_RESOURCE_NAME}")

        assert contribution is not None, f"no schema contribution for {RULES_RESOURCE_NAME}"

    def test_its_schema_describes_what_the_parser_accepts(self, contributions):
        contribution = find_contribution(contributions, f"/{RULES_RESOURCE_NAME}")
        assert contribution is not None

        ref = contribution["schema"]["$ref"]
        definitions = contributions[0]["schema"]["definitions"]
        envelope = definitions[ref.rpartition("/definitions/")[2]]

        # keep in step with `parse_package_rules()`: it rejects any other top-level key, so a key
        # it accepts but the schema doesn't would be flagged in the author's editor for no reason
        assert set(envelope["properties"]) == {"spec_version", "rules", "$schema"}
        assert envelope["additionalProperties"] is False
        assert set(envelope["required"]) == {"spec_version", "rules"}

    def test_the_two_rule_sources_share_one_rule_schema(self, contributions):
        """`rules` must mean exactly what `user_syntax_rules` means, or an author writes a valid
        rule and the parser drops it."""
        contribution = find_contribution(contributions, f"/{RULES_RESOURCE_NAME}")
        assert contribution is not None
        definitions = contributions[0]["schema"]["definitions"]
        envelope = definitions[contribution["schema"]["$ref"].rpartition("/definitions/")[2]]

        assert envelope["properties"]["rules"]["$ref"] == (
            contributions[0]["schema"]["$id"] + "#/definitions/syntax_rule_collection"
        )
