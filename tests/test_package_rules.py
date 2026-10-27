"""Tests for the reader of package-shipped syntax rules files."""

import json
import sys
from typing import Any

import pytest

from plugin import package_rules
from plugin.package_rules import SPEC_VERSION
from plugin.package_rules import find_package_rules_resources
from plugin.package_rules import load_package_rules
from plugin.package_rules import parse_package_rules
from plugin.package_rules import rules_resource_name

V1_FILE = f"Packages/MySyntax/{rules_resource_name(1)}"
V2_FILE = f"Packages/MySyntax/{rules_resource_name(2)}"

VALID_RULE: dict[str, Any] = {
    "syntaxes": ["scope:source.groovy.jenkinsfile"],
    "selector": "text.plain",
    "rules": [{"constraint": "name_contains_regex", "args": ["^Jenkinsfile(?=\\b|_)"]}],
}


def file_with(*rules: Any, **extra: Any) -> dict[str, Any]:
    return {"rules": list(rules), **extra}


def parse(data: Any, *, version: int = 1, location: str = V1_FILE):
    return parse_package_rules(data, location=location, version=version)


# ── the happy path ──────────────────────────────────────────────────────────


class TestParsePackageRules:
    def test_accepts_a_well_formed_file(self):
        rules, dropped = parse(file_with(VALID_RULE))

        assert dropped == []
        assert len(rules) == 1
        assert rules[0].syntaxes == ["scope:source.groovy.jenkinsfile"]

    def test_accepts_an_empty_rules_list(self):
        assert parse(file_with()) == ([], [])

    def test_ignores_schema_key(self):
        """`$schema` is allowed so editors outside ST can validate the file."""
        rules, dropped = parse(file_with(VALID_RULE, **{"$schema": "./schema.json"}))

        assert (len(rules), dropped) == (1, [])

    def test_keeps_rule_order(self):
        rules, _ = parse(file_with({**VALID_RULE, "comment": "first"}, {**VALID_RULE, "comment": "second"}))

        assert [rule.comment for rule in rules] == ["first", "second"]


# ── failures cost one rule, never the file ──────────────────────────────────


BAD_RULE: dict[str, Any] = {"syntaxes": "scope:source.foo", "rules": [{"constrait": "typo"}]}


class TestParsePackageRulesFailures:
    def test_one_bad_rule_does_not_cost_the_others(self):
        rules, dropped = parse(file_with(VALID_RULE, BAD_RULE))

        assert (len(rules), len(dropped)) == (1, 1)

    def test_bad_rule_is_reported_with_its_index_and_the_file(self):
        _, dropped = parse(file_with(VALID_RULE, BAD_RULE))

        assert f"invalid setting at {V1_FILE}[1]" in dropped[0].reason
        # the dropped entry carries the offending rule itself, not the whole file
        assert dropped[0].rule == BAD_RULE

    def test_non_object_file_is_rejected_whole(self):
        for data in ([], "text", 1, None):
            rules, dropped = parse(data)

            assert rules == []
            assert len(dropped) == 1
            assert V1_FILE in dropped[0].reason

    def test_an_unknown_top_level_key_is_rejected(self):
        """A typo'd "rule" for "rules" must not silently contribute nothing."""
        rules, dropped = parse({"rules": [], "typo": 1})

        assert rules == []
        assert "typo: Extra inputs are not permitted" in dropped[0].reason

    def test_the_version_is_not_accepted_as_a_field(self):
        """The version is in the file name. A stale `spec_version` left in the contents would
        otherwise silently contradict it, so it is rejected like any other unknown key."""
        _, dropped = parse({"spec_version": 1, "rules": []})

        assert "spec_version: Extra inputs are not permitted" in dropped[0].reason

    def test_our_own_field_name_is_not_silently_accepted(self):
        """`schema_` is the Python side of the `$schema` alias; it is not part of the file format."""
        _, dropped = parse({"rules": [], "schema_": "x"})

        assert "Extra inputs are not permitted" in dropped[0].reason


class TestParsePackageRulesVersions:
    def test_an_unsupported_version_is_refused_rather_than_half_parsed(self):
        """`load_package_rules()` never passes one, so this only guards a future caller."""
        rules, dropped = parse(file_with(VALID_RULE), version=SPEC_VERSION + 1, location=V2_FILE)

        assert rules == []
        assert f"cannot read the v{SPEC_VERSION + 1} format" in dropped[0].reason


# ── discovery ───────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_packages(monkeypatch):
    """Simulate a ST packages directory: readable resources, plus ones that fail to load."""
    sublime = sys.modules["sublime"]
    files: dict[str, str] = {}
    unreadable: set[str] = set()

    monkeypatch.setattr(sublime, "find_resources", lambda pattern: [*reversed(list(files)), *unreadable])

    def load_resource(name: str) -> str:
        if name in unreadable:
            raise OSError(name)
        return files[name]

    monkeypatch.setattr(sublime, "load_resource", load_resource)

    class FakePackages:
        readable = files
        broken = unreadable

        @staticmethod
        def write(package: str, *rules: Any, version: int = 1, **extra: Any) -> str:
            path = f"Packages/{package}/{rules_resource_name(version)}"
            files[path] = json.dumps(file_with(*rules, **extra))
            return path

    return FakePackages()


class TestFindPackageRulesResources:
    def test_groups_the_files_of_a_package_by_version(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE, version=1)
        fake_packages.write("Alpha", VALID_RULE, version=2)
        fake_packages.write("Zebra", VALID_RULE, version=1)

        assert find_package_rules_resources() == {
            "Alpha": {
                1: "Packages/Alpha/AutoSetSyntax.rules.v1.sublime-settings",
                2: "Packages/Alpha/AutoSetSyntax.rules.v2.sublime-settings",
            },
            "Zebra": {1: "Packages/Zebra/AutoSetSyntax.rules.v1.sublime-settings"},
        }

    def test_packages_come_out_sorted(self, fake_packages):
        fake_packages.write("Zebra", VALID_RULE)
        fake_packages.write("Alpha", VALID_RULE)

        assert list(find_package_rules_resources()) == ["Alpha", "Zebra"]

    def test_a_disabled_package_is_left_out(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.write("Zebra", VALID_RULE)

        assert list(find_package_rules_resources(disabled_packages={"Zebra"})) == ["Alpha"]

    def test_skips_our_own_file_and_the_user_package(self, fake_packages, monkeypatch):
        monkeypatch.setattr(package_rules, "PLUGIN_NAME", "AutoSetSyntax")
        fake_packages.write("AutoSetSyntax", VALID_RULE)
        fake_packages.write("User", VALID_RULE)
        fake_packages.write("Alpha", VALID_RULE)

        assert list(find_package_rules_resources()) == ["Alpha"]

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

    def test_a_file_may_be_written_in_sts_json_dialect(self, fake_packages):
        """The name ends in `.sublime-settings`, so comments and trailing commas are part of what
        it promises the author -- and this is a hand-written file by definition."""
        fake_packages.readable[f"Packages/Alpha/{rules_resource_name(1)}"] = """
            {
                // the format our files use
                "rules": [
                    {
                        "syntaxes": ["scope:source.groovy.jenkinsfile"],
                        /* told apart by name, not content */
                        "rules": [{"constraint": "name_contains_regex", "args": ["^Jenkinsfile"]},],
                    },
                ],
            }
        """

        rules, dropped = load_package_rules()

        assert dropped == []
        assert len(rules) == 1

    def test_one_broken_file_does_not_cost_the_others(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.readable["Packages/Broken/AutoSetSyntax.rules.v1.sublime-settings"] = "{not json"

        rules, dropped = load_package_rules()

        assert len(rules) == 1
        assert len(dropped) == 1
        assert "Packages/Broken/AutoSetSyntax.rules.v1.sublime-settings" in dropped[0].reason

    def test_an_unreadable_file_is_reported_rather_than_raising(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE)
        fake_packages.broken.add("Packages/Locked/AutoSetSyntax.rules.v1.sublime-settings")

        rules, dropped = load_package_rules()

        assert len(rules) == 1
        assert len(dropped) == 1
        assert "Packages/Locked/AutoSetSyntax.rules.v1.sublime-settings" in dropped[0].reason

    def test_no_files_at_all_is_not_an_error(self, fake_packages):
        assert load_package_rules() == ([], [])


class TestLoadPackageRulesAcrossVersions:
    """One package may ship several format versions so that both an old and a new plugin read what
    they understand. Only one may be used, or the same rules would be applied twice."""

    def test_the_newest_supported_version_of_a_package_is_the_one_read(self, fake_packages):
        fake_packages.write("Alpha", {**VALID_RULE, "comment": "old"}, version=SPEC_VERSION)
        fake_packages.write("Alpha", {**VALID_RULE, "comment": "new"}, version=SPEC_VERSION + 1)

        rules, _ = load_package_rules()

        assert [rule.comment for rule, _ in rules] == ["old"]

    def test_a_newer_version_that_is_skipped_says_so(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE, version=1)
        fake_packages.write("Alpha", VALID_RULE, version=SPEC_VERSION + 1)

        _, dropped = load_package_rules()

        assert len(dropped) == 1
        assert f"v{SPEC_VERSION + 1}" in dropped[0].reason

    def test_a_package_with_only_an_unsupported_version_is_explained(self, fake_packages):
        fake_packages.write("Alpha", VALID_RULE, version=SPEC_VERSION + 1)

        rules, dropped = load_package_rules()

        assert rules == []
        assert len(dropped) == 1
        assert "rules format" in dropped[0].reason
        assert "update the plugin" in dropped[0].reason
