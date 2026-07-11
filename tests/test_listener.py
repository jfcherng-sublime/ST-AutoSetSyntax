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
