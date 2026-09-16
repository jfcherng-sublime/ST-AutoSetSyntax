"""Tests for the syntax detectors in plugin/commands/auto_set_syntax.py.

Detectors return a `SyntaxDecision` (or `None`) rather than touching the view, so these tests
assert on the returned decision instead of intercepting `assign_syntax_to_view()`. Where a
detector produces a decision, the *whole* `details` payload is asserted -- that dict is logged
verbatim, so partial assertions would let the log format drift unnoticed.

`find_syntax_by_syntax_like` is still stubbed: resolving a syntax name needs a real Sublime Text
syntax registry, which the test stubs don't provide.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import sublime

import plugin.commands.auto_set_syntax as mod
from plugin.commands.auto_set_syntax import SyntaxDecision
from plugin.snapshot import ViewSnapshot
from plugin.types import ListenerEvent

MockView = sys.modules["sublime"].View


def _make_view(*, valid: bool = True, syntax: sublime.Syntax | None = None) -> MagicMock:
    view = MagicMock()
    view.is_valid.return_value = valid
    view.syntax.return_value = syntax
    view.window.return_value = MagicMock()
    view.settings.return_value = MagicMock()
    return view


def _make_snapshot(content: str, *, char_count: int | None = None, syntax_name: str = "Plain Text") -> ViewSnapshot:
    return ViewSnapshot(
        view=MockView(),
        char_count=char_count if char_count is not None else len(content),
        content=content,
        first_line=content.split("\n")[0] if content else "",
        encoding="UTF-8",
        line_count=content.count("\n") + 1,
        path_obj=None,
        syntax=sublime.Syntax(name=syntax_name),
    )


def _big_json_map() -> str:
    """A JSON object large enough to clear the small-file threshold, padded *inside* the
    structure so the content still validly starts with `{"` and ends with `..."}`."""
    body = ", ".join(f'"key{i}": {i}' for i in range(200))
    return f"{{{body}}}"


def _big_json_array() -> str:
    body = ", ".join(f'"item{i}"' for i in range(200))
    return f"[{body}]"


def _big_pretty_json_map() -> str:
    """Same shape as `_big_json_map()` but pretty-printed (2-space indent, real newlines) --
    the far more common shape for a JSON file a user would actually save or paste, e.g. from
    `json.dumps(x, indent=2)`, `JSON.stringify(x, null, 2)`, or a browser's "Copy as JSON"."""
    return json.dumps({f"key{i}": i for i in range(200)}, indent=2)


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


class TestDetect:
    """The detector chain: order, and which events gate which detector."""

    @staticmethod
    def _run(monkeypatch, event: ListenerEvent, deciders: set[str]) -> str | None:
        """Let only the detectors named in `deciders` produce a decision; report which one won."""
        names = (
            "_detect_for_st_syntax_test",
            "_detect_with_plugin_rules",
            "_detect_with_first_line",
            "_detect_with_trimmed_filename",
            "_detect_with_magika",
            "_detect_with_heuristics",
        )
        for name in names:
            decision = SyntaxDecision(sublime.Syntax(name="Python"), {"reason": name}) if name in deciders else None
            monkeypatch.setattr(mod, name, lambda *a, _d=decision, **kw: _d)

        result = mod._detect(MagicMock(), MagicMock(), event, {})
        return result.details["reason"] if result else None

    def test_first_detector_to_decide_wins(self, monkeypatch):
        assert self._run(monkeypatch, ListenerEvent.LOAD, {"_detect_with_plugin_rules", "_detect_with_first_line"}) == (
            "_detect_with_plugin_rules"
        )

    def test_syntax_test_outranks_everything(self, monkeypatch):
        deciders = {"_detect_for_st_syntax_test", "_detect_with_plugin_rules"}
        assert self._run(monkeypatch, ListenerEvent.LOAD, deciders) == "_detect_for_st_syntax_test"

    def test_falls_through_to_heuristics_when_nothing_else_decides(self, monkeypatch):
        assert self._run(monkeypatch, ListenerEvent.LOAD, {"_detect_with_heuristics"}) == "_detect_with_heuristics"

    def test_no_detector_decides(self, monkeypatch):
        assert self._run(monkeypatch, ListenerEvent.LOAD, set()) is None

    def test_trimmed_filename_is_gated_to_file_events(self, monkeypatch):
        """The file is on disk for SAVE but not necessarily for MODIFY, so filename-trimming
        must not run on the latter."""
        assert self._run(monkeypatch, ListenerEvent.SAVE, {"_detect_with_trimmed_filename"}) == (
            "_detect_with_trimmed_filename"
        )
        assert self._run(monkeypatch, ListenerEvent.MODIFY, {"_detect_with_trimmed_filename"}) is None

    def test_magika_is_gated_to_file_and_modify_events(self, monkeypatch):
        assert self._run(monkeypatch, ListenerEvent.MODIFY, {"_detect_with_magika"}) == "_detect_with_magika"
        assert self._run(monkeypatch, ListenerEvent.RELOAD, {"_detect_with_magika"}) is None


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
        monkeypatch.setattr(mod, "_detect_for_exec_output", lambda *a, **kw: SyntaxDecision(syntax, {"r": "exec"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.EXEC) is True
        assert snapshots == []
        view.assign_syntax.assert_called_once_with(syntax)

    def test_new_event_uses_the_new_view_detector(self, monkeypatch):
        view = self._prepare(monkeypatch)
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "_detect_for_new_view", lambda *a, **kw: SyntaxDecision(syntax, {"r": "new"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.NEW) is True
        view.assign_syntax.assert_called_once_with(syntax)

    def test_a_decision_from_the_chain_is_applied(self, monkeypatch):
        view = self._prepare(monkeypatch)
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "_detect", lambda *a, **kw: SyntaxDecision(syntax, {"r": "chain"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is True
        view.assign_syntax.assert_called_once_with(syntax)

    def test_no_decision_gives_up_without_touching_the_view(self, monkeypatch):
        view = self._prepare(monkeypatch)
        monkeypatch.setattr(mod, "_detect", lambda *a, **kw: None)

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is False
        view.assign_syntax.assert_not_called()

    def test_unsyntaxable_view_is_rejected_before_the_snapshot(self, monkeypatch):
        view = self._prepare(monkeypatch, syntaxable=False)
        monkeypatch.setattr(mod, "_detect", lambda *a, **kw: None)

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD) is False

    def test_skip_syntaxable_check_bypasses_that_rejection(self, monkeypatch):
        view = self._prepare(monkeypatch, syntaxable=False)
        syntax = sublime.Syntax(name="Python")
        monkeypatch.setattr(mod, "_detect", lambda *a, **kw: SyntaxDecision(syntax, {"r": "chain"}))

        assert mod.run_auto_set_syntax_on_view(view, ListenerEvent.LOAD, skip_syntaxable_check=True) is True


class TestDetectWithHeuristicsJson:
    """`is_json()` is a nested closure, exercised through the outer `_detect_with_heuristics()`."""

    @staticmethod
    def _decide(monkeypatch, content: str, *, char_count: int | None = None) -> SyntaxDecision | None:
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="JSON"))
        snap = _make_snapshot(content, char_count=char_count)
        return mod._detect_with_heuristics(snap, ListenerEvent.LOAD)

    def _detected(self, monkeypatch, content: str, *, char_count: int | None = None) -> bool:
        return self._decide(monkeypatch, content, char_count=char_count) is not None

    def test_plain_json_map_detected(self, monkeypatch):
        assert self._detected(monkeypatch, _big_json_map()) is True

    def test_decision_carries_the_full_details_payload(self, monkeypatch):
        decision = self._decide(monkeypatch, _big_json_map())
        assert decision is not None
        assert decision.details == {"event": ListenerEvent.LOAD, "reason": "heuristics"}
        assert decision.status_message is None

    def test_plain_json_array_detected(self, monkeypatch):
        assert self._detected(monkeypatch, _big_json_array()) is True

    def test_nested_array_of_arrays_detected(self, monkeypatch):
        content = "[" + ", ".join(f"[{i}, {i + 1}]" for i in range(200)) + "]"
        assert self._detected(monkeypatch, content) is True

    def test_array_of_maps_detected(self, monkeypatch):
        content = "[" + ", ".join(f'{{"k": {i}}}' for i in range(200)) + "]"
        assert self._detected(monkeypatch, content) is True

    def test_json_with_long_leading_and_trailing_whitespace_padding_detected(self, monkeypatch):
        """Regression: content[:10]/content[-10:] were sliced *before* stripping whitespace, so
        >= 10 chars of leading/trailing blank-line padding swallowed the slice window entirely
        and hid real JSON content from the begin/end regexes."""
        content = ("\n" * 15) + _big_json_map() + ("\n" * 15)
        assert self._detected(monkeypatch, content) is True

    def test_json_with_short_whitespace_padding_still_detected(self, monkeypatch):
        content = "  \n" + _big_json_map() + "\n  "
        assert self._detected(monkeypatch, content) is True

    def test_pretty_printed_json_map_detected(self, monkeypatch):
        """Regression: the begin/end regexes required the opening `{`/closing `}` to be
        immediately adjacent to a quote/value with no whitespace at all (`^\\{"` / `...\\}$`), so
        pretty-printed JSON -- `{\\n  "key": ...\\n}` -- never matched despite being the most
        common real-world shape of a JSON file."""
        assert self._detected(monkeypatch, _big_pretty_json_map()) is True

    def test_pretty_printed_json_array_of_strings_detected(self, monkeypatch):
        content = json.dumps([f"item{i}" for i in range(200)], indent=2)
        assert self._detected(monkeypatch, content) is True

    def test_pretty_printed_nested_array_of_arrays_detected(self, monkeypatch):
        content = json.dumps([[i, i + 1] for i in range(200)], indent=2)
        assert self._detected(monkeypatch, content) is True

    def test_pretty_printed_array_of_maps_detected(self, monkeypatch):
        content = json.dumps([{"k": i} for i in range(200)], indent=2)
        assert self._detected(monkeypatch, content) is True

    def test_pretty_printed_json_with_tab_indent_detected(self, monkeypatch):
        content = json.dumps({f"key{i}": i for i in range(200)}, indent="\t")
        assert self._detected(monkeypatch, content) is True

    def test_non_json_content_not_detected(self, monkeypatch):
        content = "just some plain text file\n" * 200
        assert self._detected(monkeypatch, content) is False

    def test_small_json_looking_file_not_detected(self, monkeypatch):
        """`is_small_file` gates the regex-based checks -- a tiny file that merely looks like
        JSON shouldn't be reclassified (too easy to false-positive on short snippets)."""
        content = '{"a": 1}'
        assert self._detected(monkeypatch, content, char_count=10) is False

    def test_xssi_prefix_detected_even_when_small(self, monkeypatch):
        """The XSSI-prefix check intentionally bypasses the small-file gate."""
        content = ")]}'\n" + '{"a": 1}'
        assert self._detected(monkeypatch, content, char_count=10) is True

    def test_non_plaintext_syntax_never_reclassified(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="JSON"))

        snap = _make_snapshot(_big_json_map(), syntax_name="Python")
        assert mod._detect_with_heuristics(snap, ListenerEvent.LOAD) is None


class TestDetectForExecOutput:
    def test_decides_when_the_panel_is_still_plain_text(self, monkeypatch):
        syntax = sublime.Syntax(name="Build Output")
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: syntax)
        view = _make_view(syntax=sublime.Syntax(scope="text.plain"))

        decision = mod._detect_for_exec_output(view, ListenerEvent.EXEC, {"exec_file_syntax": "scope:source.build"})

        assert decision is not None
        assert decision.syntax is syntax
        assert decision.details == {
            "event": ListenerEvent.EXEC,
            "reason": "exec output",
            "exec_file_syntax": "scope:source.build",
        }

    def test_a_panel_already_given_a_real_syntax_is_left_alone(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Build Output"))
        view = _make_view(syntax=sublime.Syntax(scope="source.python"))

        assert mod._detect_for_exec_output(view, ListenerEvent.EXEC, {"exec_file_syntax": "x"}) is None

    def test_unset_exec_file_syntax_decides_nothing(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Build Output"))
        view = _make_view(syntax=sublime.Syntax(scope="text.plain"))

        assert mod._detect_for_exec_output(view, ListenerEvent.EXEC, {}) is None

    def test_invalid_view_decides_nothing(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Build Output"))
        view = _make_view(valid=False, syntax=sublime.Syntax(scope="text.plain"))

        assert mod._detect_for_exec_output(view, ListenerEvent.EXEC, {"exec_file_syntax": "x"}) is None


class TestDetectForNewView:
    def test_decides_from_new_file_syntax(self, monkeypatch):
        syntax = sublime.Syntax(name="Markdown")
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: syntax)
        snap = _make_snapshot("")

        decision = mod._detect_for_new_view(snap, ListenerEvent.NEW, {"new_file_syntax": "scope:text.html.markdown"})

        assert decision is not None
        assert decision.details == {
            "event": ListenerEvent.NEW,
            "reason": "new file",
            "new_file_syntax": "scope:text.html.markdown",
        }

    def test_unset_new_file_syntax_decides_nothing(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Markdown"))

        assert mod._detect_for_new_view(_make_snapshot(""), ListenerEvent.NEW, {}) is None

    def test_unresolvable_new_file_syntax_decides_nothing(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: None)

        assert mod._detect_for_new_view(_make_snapshot(""), ListenerEvent.NEW, {"new_file_syntax": "nope"}) is None


def _syntax_test_snapshot(filename: str, first_line: str) -> ViewSnapshot:
    return ViewSnapshot(
        view=_make_view(syntax=sublime.Syntax(name="Plain Text")),
        char_count=len(first_line),
        content=first_line,
        first_line=first_line,
        encoding="UTF-8",
        line_count=1,
        path_obj=Path(f"/some/dir/{filename}"),
        syntax=sublime.Syntax(name="Plain Text"),
    )


class TestDetectForStSyntaxTest:
    def test_decides_from_the_syntax_under_test(self, monkeypatch):
        queried: list[str] = []

        def _fake_find(syntax_like, **kwargs):
            queried.append(str(syntax_like))
            return sublime.Syntax(name="Python")

        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", _fake_find)
        snap = _syntax_test_snapshot("syntax_test_python.py", '# SYNTAX TEST "Packages/Python/Python.sublime-syntax"')

        decision = mod._detect_for_st_syntax_test(snap, ListenerEvent.LOAD)

        assert decision is not None
        assert queried == ["Packages/Python/Python.sublime-syntax"]
        assert decision.details == {"event": ListenerEvent.LOAD, "reason": "Sublime Test syntax test file"}

    def test_a_file_not_named_syntax_test_is_ignored(self, monkeypatch):
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Python"))
        snap = _syntax_test_snapshot("regular.py", '# SYNTAX TEST "Packages/Python/Python.sublime-syntax"')

        assert mod._detect_for_st_syntax_test(snap, ListenerEvent.LOAD) is None

    def test_an_unresolvable_syntax_under_test_is_logged_not_decided(self, monkeypatch):
        """The user named a syntax that doesn't exist -- worth a log line, but there's nothing
        to decide. The diagnostic stays inside the detector."""
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: None)
        logged: list[str] = []
        monkeypatch.setattr(mod.Logger, "log", lambda msg, **kw: logged.append(str(msg)))
        snap = _syntax_test_snapshot("syntax_test_nope.py", '# SYNTAX TEST "Packages/Nope/Nope.sublime-syntax"')

        assert mod._detect_for_st_syntax_test(snap, ListenerEvent.LOAD) is None
        assert any("Cannot find the syntax under test" in line for line in logged)


class TestDetectWithPluginRules:
    def test_decides_from_the_first_matching_syntax_rule(self):
        syntax = sublime.Syntax(name="INI")
        rule = MagicMock()
        rule.syntax = syntax
        collection = MagicMock()
        collection.test.return_value = rule

        decision = mod._detect_with_plugin_rules(_make_snapshot(""), collection, ListenerEvent.LOAD)

        assert decision is not None
        assert decision.syntax is syntax
        assert decision.details == {"event": ListenerEvent.LOAD, "reason": "plugin rule", "rule": rule}

    def test_no_matching_rule_decides_nothing(self):
        collection = MagicMock()
        collection.test.return_value = None

        assert mod._detect_with_plugin_rules(_make_snapshot(""), collection, ListenerEvent.LOAD) is None


def _modeline_snapshot(content: str) -> ViewSnapshot:
    return ViewSnapshot(
        view=MockView(),
        char_count=len(content),
        content=content,
        first_line=content,
        encoding="UTF-8",
        line_count=1,
        path_obj=None,
        syntax=sublime.Syntax(name="Plain Text"),
    )


def _queried_mode_name(monkeypatch, first_line: str, settings: dict | None = None) -> str | None:
    """Run `_detect_with_first_line()` and report which mode name it looked up.

    `find_syntax_for_file` is stubbed to None so only the modeline path (not the
    general-first-line fallback) can produce a match, and `find_syntax_by_syntax_like` records
    what it was queried with -- this isolates mode-name extraction from real syntax lookup.
    """
    monkeypatch.setattr(mod.sublime, "find_syntax_for_file", lambda *a, **kw: None, raising=False)

    queried: list[str] = []

    def _fake_find(syntax_like, **kwargs):
        queried.append(str(syntax_like))
        return sublime.Syntax(name=str(syntax_like))

    monkeypatch.setattr(mod, "find_syntax_by_syntax_like", _fake_find)

    snap = _modeline_snapshot(first_line)
    mod._detect_with_first_line(snap, ListenerEvent.LOAD, settings if settings is not None else {"modeline_lines": 5})
    return queried[0] if queried else None


class TestDetectWithFirstLineEmacsModeline:
    """`_prefer_modeline`'s Emacs branch, exercised through `_detect_with_first_line()`."""

    def test_bare_mode_name_short_form(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# -*- python -*-") == "python"

    def test_mode_key_value_form(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# -*- mode: python -*-") == "python"

    def test_mode_key_first_among_multiple_vars(self, monkeypatch):
        """Regression: the old regex's greedy capture grabbed the whole "key: value; ..." list
        instead of just the mode name, so a syntax literally named "mode: python; coding: utf-8"
        was looked up (and never found) instead of "python"."""
        assert _queried_mode_name(monkeypatch, "# -*- mode: python; coding: utf-8 -*-") == "python"

    def test_mode_key_last_among_multiple_vars(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# -*- coding: utf-8; mode: python -*-") == "python"

    def test_mode_keyword_is_case_insensitive(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# -*- Mode: Python -*-") == "Python"

    def test_no_mode_key_present_resolves_nothing(self, monkeypatch):
        """A "key: value" list with no "mode" key has no mode name to use -- must not fall back
        to treating the whole list (e.g. "coding: utf-8") as if it were one."""
        assert _queried_mode_name(monkeypatch, "# -*- coding: utf-8 -*-") is None

    def test_decision_names_the_checker_that_produced_it(self, monkeypatch):
        """The reason string embeds `checker.__name__`, so the log says which of the three
        first-line strategies actually fired."""
        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", lambda *a, **kw: None, raising=False)
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="Python"))

        decision = mod._detect_with_first_line(
            _modeline_snapshot("# -*- mode: python -*-"),
            ListenerEvent.LOAD,
            {"modeline_lines": 5},
        )

        assert decision is not None
        assert decision.details == {
            "event": ListenerEvent.LOAD,
            "reason": 'syntax "first_line_match" or "file_extensions" by _prefer_modeline',
        }


class TestDetectWithFirstLineVimModeline:
    """`_prefer_modeline`'s VIM branch, same isolation approach as the Emacs test class above."""

    def test_syntax_key_followed_by_more_options(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# vim: syntax=python ts=4") == "python"

    def test_ft_alias(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# vim: ft=python") == "python"

    def test_modeline_as_last_line_with_no_trailing_newline(self, monkeypatch):
        """Regression: the old regex required a whitespace character after the syntax value
        (`(?=\\s)`), so a modeline on the file's last line with no trailing newline (a common
        "no newline at end of file" case) had nothing after it to satisfy that lookahead and
        silently failed to match."""
        assert _queried_mode_name(monkeypatch, "# some code\n# vim: syntax=python") == "python"

    def test_modeline_as_last_line_with_trailing_newline(self, monkeypatch):
        assert _queried_mode_name(monkeypatch, "# some code\n# vim: syntax=python\n") == "python"


class TestDetectWithFirstLineModelineLinesSetting:
    """Regression: `_detect_with_first_line()` did `int((...).get("modeline_lines", 5))`.
    A "modeline_lines" key explicitly set to `null` is present with value None, not absent, so
    the `.get(..., 5)` default doesn't cover it -- `int(None)` raised TypeError for every
    LOAD/SAVE/NEW/etc. event."""

    def test_null_modeline_lines_does_not_raise_and_falls_back_to_default(self, monkeypatch):
        result = _queried_mode_name(monkeypatch, "# vim: syntax=python", {"modeline_lines": None})
        assert result == "python"

    def test_zero_modeline_lines_is_preserved_as_no_search(self, monkeypatch):
        """`modeline_lines: 0` is a distinct, valid "no modeline search at all" setting (see
        head_tail_lines()'s `n == 0` case) and must not be silently coerced into the default."""
        result = _queried_mode_name(monkeypatch, "# vim: syntax=python", {"modeline_lines": 0})
        assert result is None


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


class TestDetectWithTrimmedFilename:
    @staticmethod
    def _make_snapshot_for_trimming(filename: str) -> ViewSnapshot:
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.file_name.return_value = f"/some/dir/{filename}"
        return ViewSnapshot(
            view=view,
            char_count=0,
            content="",
            first_line="",
            encoding="UTF-8",
            line_count=1,
            path_obj=None,
            syntax=sublime.Syntax(name="Plain Text"),
        )

    def test_trims_configured_suffix_and_finds_syntax(self, monkeypatch):
        snap = self._make_snapshot_for_trimming("app.js.min")
        settings = {"trim_suffixes": (".min",), "trim_suffixes_auto": False}

        def _fake_find_syntax(filename):
            return sublime.Syntax(name="JavaScript") if filename == "app.js" else sublime.Syntax(name="Plain Text")

        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", _fake_find_syntax, raising=False)

        decision = mod._detect_with_trimmed_filename(snap, ListenerEvent.SAVE, settings)

        assert decision is not None
        assert decision.details == {
            "event": ListenerEvent.SAVE,
            "reason": "trimmed filename",
            "filename_original": "app.js.min",
            "filename_trimmed": "app.js",
            "trim_suffixes": (".min",),
            "trim_suffixes_auto": False,
        }

    def test_no_matching_suffix_returns_no_decision(self, monkeypatch):
        snap = self._make_snapshot_for_trimming("app.js")
        settings = {"trim_suffixes": (".min",), "trim_suffixes_auto": False}

        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", lambda *a, **kw: None, raising=False)

        assert mod._detect_with_trimmed_filename(snap, ListenerEvent.SAVE, settings) is None

    def test_trimmed_match_that_is_still_plaintext_is_rejected(self, monkeypatch):
        """A trimmed candidate resolving back to Plain Text isn't a real match -- must keep
        trying other candidates / suffixes instead of "succeeding" with a no-op syntax."""
        snap = self._make_snapshot_for_trimming("app.js.min.min")
        settings = {"trim_suffixes": (".min",), "trim_suffixes_auto": False}

        def _fake_find_syntax(filename):
            if filename == "app.js":
                return sublime.Syntax(name="JavaScript")
            return sublime.Syntax(name="Plain Text")

        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", _fake_find_syntax, raising=False)

        decision = mod._detect_with_trimmed_filename(snap, ListenerEvent.SAVE, settings)

        assert decision is not None
        assert decision.details["filename_trimmed"] == "app.js"

    def test_non_plaintext_current_syntax_skips_entirely(self):
        """Only applies when the view's *current* syntax is still Plain Text -- a file already
        classified as something else shouldn't get reclassified by filename-trimming."""
        view = _make_view(syntax=sublime.Syntax(name="Python"))
        view.file_name.return_value = "/some/dir/app.min.js"
        snap = ViewSnapshot(
            view=view,
            char_count=0,
            content="",
            first_line="",
            encoding="UTF-8",
            line_count=1,
            path_obj=None,
            syntax=sublime.Syntax(name="Python"),
        )

        assert mod._detect_with_trimmed_filename(snap, ListenerEvent.SAVE, {}) is None

    def test_unsaved_buffer_with_no_file_name_returns_no_decision(self):
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.file_name.return_value = ""
        snap = ViewSnapshot(
            view=view,
            char_count=0,
            content="",
            first_line="",
            encoding="UTF-8",
            line_count=1,
            path_obj=None,
            syntax=sublime.Syntax(name="Plain Text"),
        )

        assert mod._detect_with_trimmed_filename(snap, ListenerEvent.SAVE, {}) is None


class _FakeMagikaResult:
    def __init__(self, *, ok: bool = True, status: str = "", label: str = "python", score: float = 0.9) -> None:
        self.ok = ok
        self.status = status
        self.dl = MagicMock(label=label)
        self.score = score

    def __repr__(self) -> str:
        return f"<FakeMagikaResult label={self.dl.label} score={self.score}>"


class TestDetectWithMagika:
    @staticmethod
    def _make_magika_snapshot(
        *, content: str = "print(1)\nprint(2)\n", dirty: bool = False, path: str | None = "/tmp/foo"
    ) -> ViewSnapshot:
        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.is_dirty.return_value = dirty
        return ViewSnapshot(
            view=view,
            char_count=len(content),
            content=content,
            first_line=content.split("\n")[0],
            encoding="UTF-8",
            line_count=content.count("\n") + 1,
            path_obj=Path(path) if path else None,
            syntax=sublime.Syntax(name="Plain Text"),
        )

    @staticmethod
    def _install_magika(monkeypatch, magika_obj):
        monkeypatch.setattr(mod, "get_magika_object", lambda: magika_obj)
        monkeypatch.setattr(
            mod,
            "resolve_magika_label_with_syntax_map",
            lambda label, syntax_map: [f"scope:source.{label}"],
        )
        monkeypatch.setattr(mod, "find_syntax_by_syntax_likes", lambda likes, **kw: sublime.Syntax(name="Python"))

    def test_disabled_setting_short_circuits(self, monkeypatch):
        magika_obj = MagicMock()
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": False}) is None
        magika_obj.identify_path.assert_not_called()
        magika_obj.identify_bytes.assert_not_called()

    def test_happy_path_decides_with_details_and_status_message(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()

        decision = mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True})

        assert decision is not None
        assert decision.details == {"event": ListenerEvent.LOAD, "reason": "Magika (Deep Learning)"}
        assert decision.status_message == "Predicted label: python (90.0% confidence)"

    def test_detector_does_not_emit_the_status_message_itself(self, monkeypatch):
        """Output is `_apply()`'s job -- the detector only decides what would be said."""
        messages: list[str] = []
        monkeypatch.setattr(mod.sublime, "status_message", messages.append, raising=False)

        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)

        mod._detect_with_magika(self._make_magika_snapshot(), ListenerEvent.LOAD, {"magika.enabled": True})

        assert messages == []

    def test_score_below_threshold_returns_no_decision(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.3)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()
        settings = {"magika.enabled": True, "magika.min_confidence": 0.5}

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, settings) is None

    def test_ignored_label_returns_no_decision(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="txt", score=0.99)
        self._install_magika(monkeypatch, magika_obj)
        monkeypatch.setattr(mod, "get_magika_ignored_labels", lambda: {"txt"})
        snap = self._make_magika_snapshot()

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is None

    def test_failed_identification_returns_no_decision(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(ok=False, status="error")
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is None

    def test_modify_event_single_line_content_skipped(self, monkeypatch):
        """Guards against reclassifying mid-typing on the very first line, e.g. right after
        typing "import" -- too early to tell Python from JS/TS."""
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(content="import ", dirty=True)

        assert mod._detect_with_magika(snap, ListenerEvent.MODIFY, {"magika.enabled": True}) is None
        magika_obj.identify_bytes.assert_not_called()

    def test_modify_event_multi_line_content_proceeds(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(content="import os\nprint(os.getcwd())\n", dirty=True)

        assert mod._detect_with_magika(snap, ListenerEvent.MODIFY, {"magika.enabled": True}) is not None

    def test_extensioned_file_skipped_unless_command_event(self, monkeypatch):
        """Files that already have an extension get their syntax from that extension via ST's
        own resolution -- magika is meant for extensionless files, except when the user
        explicitly invokes the command (COMMAND event bypasses the extension check)."""
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)

        view = _make_view(syntax=sublime.Syntax(name="Plain Text"))
        view.is_dirty.return_value = False
        snap = ViewSnapshot(
            view=view,
            char_count=10,
            content="print(1)\n",
            first_line="print(1)",
            encoding="UTF-8",
            line_count=2,
            path_obj=Path("/tmp/foo.txt"),
            syntax=sublime.Syntax(name="Plain Text"),
        )

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is None
        magika_obj.identify_path.assert_not_called()

        assert mod._detect_with_magika(snap, ListenerEvent.COMMAND, {"magika.enabled": True}) is not None

    def test_dirty_buffer_uses_identify_bytes_not_identify_path(self, monkeypatch):
        """A dirty (unsaved-changes) buffer's on-disk content is stale -- must analyze the live
        in-memory content instead of re-reading the (outdated) file from disk."""
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(dirty=True)

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is not None
        magika_obj.identify_path.assert_not_called()
        magika_obj.identify_bytes.assert_called_once()

    def test_clean_buffer_with_path_uses_identify_path(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(dirty=False)

        assert mod._detect_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is not None
        magika_obj.identify_bytes.assert_not_called()
        magika_obj.identify_path.assert_called_once()
