"""Tests for the v1 parser of package-provided rules files."""

import json
import sys
from typing import Any

import pytest

from plugin import package_rules
from plugin.package_rules import SPEC_VERSION
from plugin.package_rules import find_package_rules_resources
from plugin.package_rules import load_package_rules
from plugin.package_rules import parse_package_rules

LOCATION = "Packages/MySyntax/AutoSetSyntax.rules.sublime-settings"

VALID_RULE: dict[str, Any] = {
    "syntaxes": ["scope:source.groovy.jenkinsfile"],
    "selector": "text.plain",
    "rules": [{"constraint": "name_contains_regex", "args": ["^Jenkinsfile(?=\\b|_)"]}],
}


def file_with(*rules: Any, **extra: Any) -> dict[str, Any]:
    return {"spec_version": SPEC_VERSION, "rules": list(rules), **extra}


# ── the happy path ──────────────────────────────────────────────────────────


class TestParsePackageRules:
    def test_accepts_a_well_formed_file(self):
        rules, dropped = parse_package_rules(file_with(VALID_RULE), location=LOCATION)

        assert dropped == []
        assert len(rules) == 1
        assert rules[0].syntaxes == ["scope:source.groovy.jenkinsfile"]

    def test_accepts_an_empty_rules_list(self):
        rules, dropped = parse_package_rules(file_with(), location=LOCATION)

        assert (rules, dropped) == ([], [])

    def test_ignores_schema_key(self):
        """`$schema` is allowed so editors outside ST can validate the file."""
        rules, dropped = parse_package_rules(file_with(VALID_RULE, **{"$schema": "./schema.json"}), location=LOCATION)

        assert (len(rules), dropped) == (1, [])

    def test_keeps_rule_order(self):
        first = {**VALID_RULE, "comment": "first"}
        second = {**VALID_RULE, "comment": "second"}

        rules, _ = parse_package_rules(file_with(first, second), location=LOCATION)

        assert [rule.comment for rule in rules] == ["first", "second"]


# ── failures cost one rule, never the file ──────────────────────────────────


class TestParsePackageRulesFailures:
    def test_one_bad_rule_does_not_cost_the_others(self):
        rules, dropped = parse_package_rules(
            file_with(VALID_RULE, {"syntaxes": "scope:source.foo", "rules": [{"constrait": "typo"}]}),
            location=LOCATION,
        )

        assert len(rules) == 1
        assert len(dropped) == 1

    def test_bad_rule_is_reported_with_its_index_and_the_file(self):
        _, dropped = parse_package_rules(
            file_with(VALID_RULE, {"syntaxes": "scope:source.foo", "rules": [{"constrait": "typo"}]}),
            location=LOCATION,
        )

        assert f"invalid setting at {LOCATION}[1]" in dropped[0].reason
        # the dropped entry carries the offending rule itself, not the whole file
        assert dropped[0].rule == {"syntaxes": "scope:source.foo", "rules": [{"constrait": "typo"}]}

    def test_non_object_file_is_rejected_whole(self):
        for data in ([], "text", 1, None):
            rules, dropped = parse_package_rules(data, location=LOCATION)

            assert rules == []
            assert len(dropped) == 1
            assert LOCATION in dropped[0].reason

    def test_an_unknown_top_level_key_is_rejected(self):
        """A typo'd "rule" for "rules" must not silently contribute nothing."""
        rules, dropped = parse_package_rules({"spec_version": SPEC_VERSION, "rules": [], "typo": 1}, location=LOCATION)

        assert rules == []
        assert "typo: Extra inputs are not permitted" in dropped[0].reason

    def test_our_own_field_name_is_not_silently_accepted(self):
        """`schema_` is the Python side of the `$schema` alias; it is not part of the file format."""
        _, dropped = parse_package_rules({"spec_version": SPEC_VERSION, "rules": [], "schema_": "x"}, location=LOCATION)

        assert "Extra inputs are not permitted" in dropped[0].reason


# ── the version gate ────────────────────────────────────────────────────────
#
# A `spec_version` is deliberately closed, not an open range: a file written against a version this
# plugin has no parser for is skipped whole, with one sentence saying how to fix it. Skipped, not
# guessed at -- the whole reason the field exists. A future v2 therefore means adding a parser here
# (see `_ENVELOPE_PARSERS`) rather than widening what v1 accepts.


class TestSpecVersion:
    @pytest.mark.parametrize("version", [True, False, "1", 1.0, 1.5, None, [1]])
    def test_rejects_a_non_integer_version(self, version):
        rules, dropped = parse_package_rules({"spec_version": version, "rules": [VALID_RULE]}, location=LOCATION)

        assert rules == []
        assert 'no integer "spec_version"' in dropped[0].reason

    def test_a_missing_version_is_not_silently_treated_as_v1(self):
        rules, dropped = parse_package_rules({"rules": [VALID_RULE]}, location=LOCATION)

        assert rules == []
        assert 'no integer "spec_version"' in dropped[0].reason

    def test_a_newer_version_skips_the_file_whole(self):
        rules, dropped = parse_package_rules(
            {"spec_version": SPEC_VERSION + 1, "rules": [VALID_RULE], "envelope_key_of_the_future": 1},
            location=LOCATION,
        )

        assert rules == []
        assert len(dropped) == 1
        assert f"declares spec_version {SPEC_VERSION + 1}" in dropped[0].reason

    def test_a_newer_version_is_not_reported_as_a_schema_error(self):
        """The one sentence explaining the version must not be buried under "extra inputs" errors."""
        _, dropped = parse_package_rules(
            {"spec_version": SPEC_VERSION + 1, "rules": [VALID_RULE], "envelope_key_of_the_future": 1},
            location=LOCATION,
        )

        assert "Extra inputs" not in dropped[0].reason

    @pytest.mark.parametrize("version", [0, -1])
    def test_a_non_positive_version_is_rejected(self, version):
        rules, dropped = parse_package_rules({"spec_version": version, "rules": [VALID_RULE]}, location=LOCATION)

        assert rules == []
        assert "is not a spec version" in dropped[0].reason


# ── discovery ───────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_packages(monkeypatch):
    """Simulate a ST packages directory: readable resources, plus ones that fail to load."""
    sublime = sys.modules["sublime"]
    files: dict[str, str] = {}
    unreadable: set[str] = set()

    def find_resources(pattern: str) -> list[str]:
        assert pattern == "AutoSetSyntax.rules.sublime-settings"
        # unsorted on purpose: discovery is responsible for a stable order
        return [*reversed(list(files)), *unreadable]

    def load_resource(name: str) -> str:
        if name in unreadable:
            raise OSError(f"cannot read {name}")
        return files[name]

    monkeypatch.setattr(sublime, "find_resources", find_resources)
    monkeypatch.setattr(sublime, "load_resource", load_resource)

    class FakePackages:
        readable = files
        broken = unreadable

        def write(self, package: str, *rules: Any, **extra: Any) -> str:
            path = f"Packages/{package}/AutoSetSyntax.rules.sublime-settings"
            files[path] = json.dumps(file_with(*rules, **extra))
            return path

    return FakePackages()


class TestFindPackageRulesResources:
    def test_returns_the_shipped_files_sorted(self, fake_packages):
        fake_packages.write("Zebra", VALID_RULE)
        fake_packages.write("Alpha", VALID_RULE)

        assert find_package_rules_resources() == [
            "Packages/Alpha/AutoSetSyntax.rules.sublime-settings",
            "Packages/Zebra/AutoSetSyntax.rules.sublime-settings",
        ]

    def test_skips_our_own_file_and_the_user_package(self, fake_packages, monkeypatch):
        monkeypatch.setattr(package_rules, "PLUGIN_NAME", "AutoSetSyntax")
        fake_packages.write("AutoSetSyntax", VALID_RULE)
        fake_packages.write("User", VALID_RULE)
        fake_packages.write("Alpha", VALID_RULE)

        assert find_package_rules_resources() == ["Packages/Alpha/AutoSetSyntax.rules.sublime-settings"]

    def test_skips_a_package_whose_name_merely_shares_our_prefix(self, fake_packages, monkeypatch):
        """`Packages/AutoSetSyntaxExtra/` is a different package and must not be excluded."""
        monkeypatch.setattr(package_rules, "PLUGIN_NAME", "AutoSetSyntax")
        fake_packages.write("AutoSetSyntaxExtra", VALID_RULE)

        assert len(find_package_rules_resources()) == 1


class TestLoadPackageRules:
    def test_loads_every_package(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.write("Zebra", VALID_RULE)

        rules, dropped = load_package_rules()

        assert (len(rules), dropped) == (2, [])

    def test_one_broken_file_does_not_cost_the_others(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.readable["Packages/Broken/AutoSetSyntax.rules.sublime-settings"] = "{not json"

        rules, dropped = load_package_rules()

        assert len(rules) == 1
        assert len(dropped) == 1
        assert "Packages/Broken/AutoSetSyntax.rules.sublime-settings" in dropped[0].reason

    def test_an_unreadable_file_is_reported_rather_than_raising(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.broken.add("Packages/Locked/AutoSetSyntax.rules.sublime-settings")

        rules, dropped = load_package_rules()

        assert len(rules) == 1
        assert len(dropped) == 1
        assert "Packages/Locked/AutoSetSyntax.rules.sublime-settings" in dropped[0].reason
        assert dropped[0].rule is None

    def test_no_files_at_all_is_not_an_error(self, fake_packages):
        assert load_package_rules() == ([], [])
