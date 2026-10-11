"""Regression tests for the "one bad input must not silently widen or disable the plugin" fixes.

- A rule with an unresolvable child must not be compiled with that child silently removed:
  removing it could leave an `all` with no children, which folds to "always matches".
- An empty (but compiled) rule collection must still count as a ready window.
- A custom implementation that fails with a non-ImportError must not abort plugin startup.
"""

import dataclasses
import importlib
import importlib.machinery
import pkgutil
from unittest.mock import MagicMock

import sublime

import plugin.commands.auto_set_syntax as auto_mod
import plugin.custom as custom_mod
import plugin.shared as shared_mod
from plugin.rules import SyntaxRuleCollection
from plugin.rules.match import MatchRule
from plugin.rules.syntax import SyntaxRule
from plugin.shared import G
from plugin.types import DroppedRule
from plugin.types import ListenerEvent
from plugin.types import StConstraintRule
from plugin.types import StMatchRule
from plugin.types import StSyntaxRule

_INVALID_RULE = StSyntaxRule(
    syntaxes=["Python"],
    match="all",
    rules=[StMatchRule(match="any", rules=[StConstraintRule(constraint="nope")])],
)


def _make_window(window_id: int) -> MagicMock:
    window = MagicMock(spec=sublime.Window)
    window.id.return_value = window_id
    return window


class TestUnresolvableChildFailsEnclosingRule:
    def test_match_with_unknown_constraint_child_is_not_made(self):
        rule = MatchRule.make(StMatchRule(match="all", rules=[StConstraintRule(constraint="is_extensoin")]))

        assert rule is None

    def test_all_with_one_valid_and_one_unknown_child_is_not_made(self):
        rule = MatchRule.make(
            StMatchRule(
                match="all",
                rules=[
                    StConstraintRule(constraint="is_extension", args=["py"]),
                    StConstraintRule(constraint="is_extensoin", args=["py"]),
                ],
            )
        )

        assert rule is None

    def test_unknown_constraint_deep_inside_fails_the_whole_syntax_rule(self):
        syntax_rule = SyntaxRule.make(_INVALID_RULE)

        assert syntax_rule.root_rule is None
        assert syntax_rule.fold().value is False

    def test_dropped_report_says_the_rule_is_invalid(self):
        dropped = DroppedRule.make(SyntaxRule.make(_INVALID_RULE))

        assert dropped.reason.startswith("never matches: it contains an unknown or invalid match/constraint")

    def test_root_optimized_away_keeps_its_own_reason(self):
        syntax_rule = SyntaxRule(syntax=sublime.Syntax(name="Python"), root_rule=None)

        assert syntax_rule.fold().reason == "no sub-rule is left to test"


class TestUnoptimizedSyntaxRuleTest:
    """`compile_rules()` falls back to an unoptimized collection, so `test()` must agree with `fold()`."""

    @staticmethod
    def _snapshot(make_snapshot):
        return dataclasses.replace(make_snapshot(), syntax=sublime.Syntax(name="Plain Text", scope="text.plain"))

    def test_invalid_rule_never_matches(self, make_snapshot, monkeypatch):
        monkeypatch.setattr(sublime, "score_selector", lambda scope, selector: 1)
        syntax_rule = SyntaxRule.make(_INVALID_RULE)
        syntax_rule.syntax = sublime.Syntax(name="Python")

        assert syntax_rule.test(self._snapshot(make_snapshot)) is False

    def test_rule_without_syntax_never_matches(self, make_snapshot, monkeypatch):
        monkeypatch.setattr(sublime, "score_selector", lambda scope, selector: 1)
        always = MatchRule.make(StMatchRule(match="all"))
        syntax_rule = SyntaxRule(syntax=None, root_rule=always)

        assert syntax_rule.test(self._snapshot(make_snapshot)) is False

    def test_valid_rule_still_matches(self, make_snapshot, monkeypatch):
        monkeypatch.setattr(sublime, "score_selector", lambda scope, selector: 1)
        always = MatchRule.make(StMatchRule(match="all"))
        syntax_rule = SyntaxRule(syntax=sublime.Syntax(name="Python"), root_rule=always)

        assert syntax_rule.test(self._snapshot(make_snapshot)) is True


class TestEmptyCollectionKeepsWindowReady:
    def test_window_with_empty_rule_collection_is_ready(self, monkeypatch):
        window = _make_window(301)
        monkeypatch.setattr(shared_mod, "get_merged_plugin_settings", lambda **kw: {"debounce": 0})
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])
        try:
            assert G.is_plugin_ready(window) is True
        finally:
            G.syntax_rule_collections.pop(window, None)

    def test_detection_still_runs_when_every_rule_was_dropped(self, monkeypatch):
        window = _make_window(302)
        view = MagicMock()
        view.window.return_value = window
        view.is_valid.return_value = True
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])

        detect = MagicMock(return_value=None)
        monkeypatch.setattr(shared_mod, "get_merged_plugin_settings", lambda **kw: {"debounce": 0})
        monkeypatch.setattr(auto_mod, "get_merged_plugin_settings", lambda **kw: {})
        monkeypatch.setattr(auto_mod, "is_syntaxable_view", lambda *a, **kw: True)
        monkeypatch.setattr(auto_mod.ViewSnapshot, "from_view", classmethod(lambda cls, v: MagicMock()))
        monkeypatch.setattr(auto_mod, "_detect", detect)
        try:
            auto_mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD)
        finally:
            G.syntax_rule_collections.pop(window, None)

        detect.assert_called_once()


class TestCustomImplementationLoadingIsFaultTolerant:
    def test_syntax_error_in_one_custom_module_does_not_stop_the_others(self, monkeypatch, tmp_path):
        matches_dir = tmp_path / "plugin-Custom" / "matches"
        monkeypatch.setattr(sublime, "packages_path", lambda: str(tmp_path))
        monkeypatch.setattr(custom_mod, "PLUGIN_CUSTOM_MODULE_PATHS", {"match": matches_dir})
        finder = importlib.machinery.FileFinder(str(matches_dir))
        monkeypatch.setattr(pkgutil, "iter_modules", lambda paths: [(finder, "broken", False), (finder, "fine", False)])

        imported: list[str] = []

        def fake_import(name: str) -> None:
            imported.append(name)
            if name.endswith(".broken"):
                raise SyntaxError("invalid syntax")

        monkeypatch.setattr(importlib, "import_module", fake_import)

        custom_mod.load_custom_implementations()  # must not raise

        assert [name.rsplit(".", 1)[-1] for name in imported] == ["broken", "fine"]
