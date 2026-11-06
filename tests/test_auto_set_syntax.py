"""Tests for running detection on a view and applying its verdict (plugin/commands/auto_set_syntax.py).

The detectors themselves are covered in test_detectors.py; here they are stubbed, so these tests
only pin down how a decision (or its absence) reaches the view.
"""

from unittest.mock import MagicMock

import sublime

import plugin.commands.auto_set_syntax as mod
from plugin.detectors import SyntaxDecision
from plugin.types import ListenerEvent


def _make_view(*, valid: bool = True, syntax: sublime.Syntax | None = None) -> MagicMock:
    view = MagicMock()
    view.is_valid.return_value = valid
    view.syntax.return_value = syntax
    view.window.return_value = MagicMock()
    view.settings.return_value = MagicMock()
    return view


class TestApply:
    """`_apply()` is the single place a decision reaches the view."""

    def test_no_decision_is_a_no_op(self):
        view = _make_view()
        assert mod._apply(view, None) is False
        view.assign_syntax.assert_not_called()

    def test_decision_is_assigned_with_its_details(self, monkeypatch):
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.buffer.return_value.views.return_value = [view]
        syntax = sublime.Syntax(name="Python")

        assert mod._apply(view, SyntaxDecision(syntax, {"reason": "test"})) is True
        view.assign_syntax.assert_called_once_with(syntax)

    def test_status_message_is_emitted_only_when_the_decision_carries_one(self, monkeypatch):
        """The status message travels on the decision so the detector decides *what* is said
        while `_apply()` decides *when* anything is said at all."""
        messages: list[str] = []
        monkeypatch.setattr(mod.sublime, "status_message", messages.append, raising=False)

        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.buffer.return_value.views.return_value = [view]
        syntax = sublime.Syntax(name="Python")

        mod._apply(view, SyntaxDecision(syntax, {"reason": "quiet"}))
        assert messages == []

        mod._apply(view, SyntaxDecision(syntax, {"reason": "loud"}, status_message="hello"))
        assert messages == ["hello"]


class TestRunAutoSetSyntaxOnView:
    """The orchestrator. Only Sublime Text's own globals are stubbed -- the detector seam itself
    is exercised, not patched around."""

    @staticmethod
    def _prepare(monkeypatch, *, ready: bool = True, syntaxable: bool = True) -> MagicMock:
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.buffer.return_value.views.return_value = [view]

        fake_g = MagicMock()
        fake_g.is_plugin_ready.return_value = ready
        fake_g.syntax_rule_collections.get.return_value = MagicMock()
        monkeypatch.setattr(mod, "G", fake_g)
        monkeypatch.setattr(mod, "get_merged_plugin_settings", lambda **kw: {})
        monkeypatch.setattr(mod, "is_syntaxable_view", lambda *a, **kw: syntaxable)
        monkeypatch.setattr(mod.ViewSnapshot, "from_view", classmethod(lambda cls, v: MagicMock()))
        return view

    def test_plugin_not_ready_bails_out(self, monkeypatch):
        view = self._prepare(monkeypatch, ready=False)
        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is False

    def test_exec_event_uses_the_exec_detector_without_a_snapshot(self, monkeypatch):
        """EXEC short-circuits before `ViewSnapshot.from_view()` -- building a snapshot for every
        build-panel update would be wasted work."""
        view = self._prepare(monkeypatch)
        snapshots = []
        monkeypatch.setattr(
            mod.ViewSnapshot, "from_view", classmethod(lambda cls, v: snapshots.append(v) or MagicMock())
        )
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "detect_for_exec_output", lambda *a, **kw: SyntaxDecision(syntax, {"r": "exec"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.EXEC) is True
        assert snapshots == []
        view.assign_syntax.assert_called_once_with(syntax)

    def test_new_event_uses_the_new_view_detector(self, monkeypatch):
        view = self._prepare(monkeypatch)
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "detect_for_new_view", lambda *a, **kw: SyntaxDecision(syntax, {"r": "new"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.NEW) is True
        view.assign_syntax.assert_called_once_with(syntax)

    def test_a_decision_from_the_chain_is_applied(self, monkeypatch):
        view = self._prepare(monkeypatch)
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "detect", lambda *a, **kw: SyntaxDecision(syntax, {"r": "chain"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is True
        view.assign_syntax.assert_called_once_with(syntax)

    def test_no_decision_gives_up_without_touching_the_view(self, monkeypatch):
        view = self._prepare(monkeypatch)
        monkeypatch.setattr(mod, "detect", lambda *a, **kw: None)

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is False
        view.assign_syntax.assert_not_called()

    def test_unsyntaxable_view_is_rejected_before_the_snapshot(self, monkeypatch):
        view = self._prepare(monkeypatch, syntaxable=False)
        monkeypatch.setattr(mod, "detect", lambda *a, **kw: None)

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is False


class TestAssignSyntaxToView:
    def test_invalid_view_returns_false_without_mutation(self):
        view = _make_view(valid=False)
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view, new_syntax) is False
        view.assign_syntax.assert_not_called()

    def test_assigns_syntax_and_marks_view(self):
        old_syntax = sublime.Syntax(name="Plain Text")
        view = _make_view(syntax=old_syntax)
        view.buffer.return_value.views.return_value = [view]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view, new_syntax) is True

        view.assign_syntax.assert_called_once_with(new_syntax)
        view.settings.return_value.set.assert_called_once_with(mod.VIEW_KEY_IS_ASSIGNED, True)

    def test_already_matching_syntax_is_not_reassigned(self):
        """The "already assigned" branch must still be a no-op mutation-wise -- only the log
        message differs, not the actual view state."""
        syntax = sublime.Syntax(name="Python")
        view = _make_view(syntax=syntax)
        view.buffer.return_value.views.return_value = [view]

        assert mod.assign_syntax_to_view(view, syntax) is True
        view.assign_syntax.assert_not_called()
        view.settings.return_value.set.assert_not_called()

    def test_view_with_no_syntax_is_treated_as_null_syntax_not_a_crash(self):
        view = _make_view(syntax=None)
        view.buffer.return_value.views.return_value = [view]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view, new_syntax) is True
        view.assign_syntax.assert_called_once_with(new_syntax)

    def test_propagates_to_all_views_sharing_the_buffer(self):
        """Clones/split-views of the same buffer are kept in sync -- a syntax change to one
        clone must apply to every view of that buffer."""
        old_syntax = sublime.Syntax(name="Plain Text")
        view1 = _make_view(syntax=old_syntax)
        view2 = _make_view(syntax=old_syntax)
        view1.buffer.return_value.views.return_value = [view1, view2]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view1, new_syntax) is True

        view1.assign_syntax.assert_called_once_with(new_syntax)
        view2.assign_syntax.assert_called_once_with(new_syntax)

    def test_caller_details_dict_is_not_mutated(self):
        """`details` arrives from a frozen `SyntaxDecision`; injecting the resolved syntax must
        not write back into the decision's dict."""
        old_syntax = sublime.Syntax(name="Plain Text")
        view = _make_view(syntax=old_syntax)
        view.buffer.return_value.views.return_value = [view]
        details = {"reason": "test"}

        assert mod.assign_syntax_to_view(view, sublime.Syntax(name="Python"), details=details) is True
        assert details == {"reason": "test"}

    def test_view_without_a_window_is_skipped(self):
        """A view that briefly has no window (e.g. mid-teardown) must be skipped, not crash.
        Documents current (accepted) behavior: the function still returns True even though
        nothing was actually assigned, since every candidate view lacked a window -- this only
        means run_auto_set_syntax_on_view() won't retry other detectors for *this* event; the
        view keeps whatever syntax it already had, and the next event re-evaluates it fresh."""
        old_syntax = sublime.Syntax(name="Plain Text")
        view = _make_view(syntax=old_syntax)
        view.window.return_value = None
        view.buffer.return_value.views.return_value = [view]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view, new_syntax) is True
        view.assign_syntax.assert_not_called()
