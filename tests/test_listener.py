"""Tests for AutoSetSyntaxEventListener's on_new/on_new_window window-setup ordering.

Regression coverage: Sublime Text fires `on_new(view)` *before* `on_new_window(window)` for a
brand new window's first tab. `on_new_window` is what compiles a window's rule collection
(`G.syntax_rule_collections`), which `run_auto_set_syntax_on_view()` requires via
`G.is_plugin_ready()`. Without ensuring setup runs first, the NEW event -- and therefore
`new_file_syntax` -- would silently never apply to a new window's first tab.
"""

from unittest.mock import MagicMock

import sublime

import plugin.listener as listener_mod
from plugin.shared import G


def _make_window(window_id: int) -> MagicMock:
    window = MagicMock(spec=sublime.Window)
    window.id.return_value = window_id
    return window


class TestEnsureWindowSetUp:
    def test_calls_set_up_window_when_not_yet_tracked(self, monkeypatch):
        window = _make_window(101)
        assert window not in G.syntax_rule_collections

        calls = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

        listener_mod._ensure_window_set_up(window)

        assert calls == [window]

    def test_skips_set_up_window_when_already_tracked(self, monkeypatch):
        from plugin.rules import SyntaxRuleCollection

        window = _make_window(102)
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])
        try:
            calls = []
            monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

            listener_mod._ensure_window_set_up(window)

            assert calls == []
        finally:
            G.syntax_rule_collections.pop(window, None)


class TestOnNewEnsuresWindowSetUpBeforeEvaluating:
    def test_on_new_sets_up_window_before_running_auto_set_syntax(self, monkeypatch):
        window = _make_window(103)
        view = MagicMock()
        view.window.return_value = window
        assert window not in G.syntax_rule_collections

        call_order = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: call_order.append("set_up_window"))
        monkeypatch.setattr(
            listener_mod,
            "run_auto_set_syntax_on_view",
            lambda v, event, **kwargs: call_order.append("run_auto_set_syntax_on_view"),
        )

        listener_mod.AutoSetSyntaxEventListener().on_new(view)

        assert call_order == ["set_up_window", "run_auto_set_syntax_on_view"]

    def test_on_new_does_not_redundantly_set_up_an_already_tracked_window(self, monkeypatch):
        from plugin.rules import SyntaxRuleCollection

        window = _make_window(104)
        G.syntax_rule_collections[window] = SyntaxRuleCollection.make([])
        try:
            view = MagicMock()
            view.window.return_value = window

            calls = []
            monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))
            monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kwargs: True)

            listener_mod.AutoSetSyntaxEventListener().on_new(view)

            assert calls == []
        finally:
            G.syntax_rule_collections.pop(window, None)


class TestOnNewWindowStillSetsUpWhenOnNewDidNotRunFirst:
    def test_on_new_window_sets_up_window_when_not_yet_tracked(self, monkeypatch):
        window = _make_window(105)
        assert window not in G.syntax_rule_collections

        calls = []
        monkeypatch.setattr(listener_mod, "set_up_window", lambda w: calls.append(w))

        listener_mod.AutoSetSyntaxEventListener().on_new_window(window)

        assert calls == [window]


class TestCompileRulesHandlesInvalidSyntaxRules:
    """Regression: StConstraintRule/StMatchRule now reject unrecognized keys (a typo'd
    "constraint" key would otherwise silently validate as a no-op StMatchRule). That means a
    single malformed rule anywhere in the user's whole syntax_rules setting raises a
    pydantic.ValidationError -- compile_rules() must catch that and fall back to an empty rule
    set instead of crashing set_up_window()/on_new_window() for the whole window."""

    def test_invalid_syntax_rules_falls_back_to_empty_collection(self, monkeypatch):
        from pydantic import TypeAdapter

        from plugin.types import StSyntaxRule

        window = _make_window(106)

        def _bad_pref_syntax_rules(*, window=None):
            # a typo'd "constraint" key, same shape as a real user config mistake
            return TypeAdapter(list[StSyntaxRule]).validate_python([
                {"rules": [{"constrait": "is_extension", "args": ["py"]}]}
            ])

        monkeypatch.setattr(listener_mod, "pref_syntax_rules", _bad_pref_syntax_rules)

        try:
            listener_mod.compile_rules(window)  # must not raise

            collection = G.syntax_rule_collections[window]
            assert len(collection) == 0
        finally:
            G.syntax_rule_collections.pop(window, None)
            G.dropped_rules_collection.pop(window, None)
