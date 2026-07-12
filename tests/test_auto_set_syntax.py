"""Tests for the syntax-assignment strategies in plugin/commands/auto_set_syntax.py.

This module is the plugin's core dispatch logic but previously had zero dedicated test
coverage (0% per `make ci-test-cov`), unlike almost everything else in the codebase.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import sublime

import plugin.commands.auto_set_syntax as mod
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


class TestAssignSyntaxWithHeuristicsJson:
    """`is_json()` is a nested closure, so it's exercised indirectly through the outer
    `_assign_syntax_with_heuristics()`, with `find_syntax_by_syntax_like`/`assign_syntax_to_view`
    stubbed out so the assertions isolate the detection heuristic itself."""

    @staticmethod
    def _detected(monkeypatch, content: str, *, char_count: int | None = None) -> bool:
        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", lambda *a, **kw: sublime.Syntax(name="JSON"))
        calls = []
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: calls.append((a, kw)) or True)

        snap = _make_snapshot(content, char_count=char_count)
        result = mod._assign_syntax_with_heuristics(snap, ListenerEvent.LOAD)

        assert result == bool(calls)  # the return value must reflect whether assignment was attempted
        return result

    def test_plain_json_map_detected(self, monkeypatch):
        assert self._detected(monkeypatch, _big_json_map()) is True

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
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        snap = _make_snapshot(_big_json_map(), syntax_name="Python")
        assert mod._assign_syntax_with_heuristics(snap, ListenerEvent.LOAD) is False


class TestAssignSyntaxWithFirstLineEmacsModeline:
    """`_prefer_modeline`'s Emacs branch is exercised indirectly through the outer
    `_assign_syntax_with_first_line()`. `find_syntax_for_file` is stubbed to None so only the
    modeline path (not the general-first-line fallback) can produce a match, and
    `find_syntax_by_syntax_like` is stubbed to record what mode name it was actually queried
    with -- this isolates the mode-name-extraction logic from real syntax lookup."""

    @staticmethod
    def _queried_mode_name(monkeypatch, first_line: str) -> str | None:
        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", lambda *a, **kw: None, raising=False)

        queried: list[str] = []

        def _fake_find(syntax_like, **kwargs):
            queried.append(str(syntax_like))
            return sublime.Syntax(name=str(syntax_like))

        monkeypatch.setattr(mod, "find_syntax_by_syntax_like", _fake_find)
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        snap = ViewSnapshot(
            view=MockView(),
            char_count=len(first_line),
            content=first_line,
            first_line=first_line,
            encoding="UTF-8",
            line_count=1,
            path_obj=None,
            syntax=sublime.Syntax(name="Plain Text"),
        )
        mod._assign_syntax_with_first_line(snap, ListenerEvent.LOAD, {"modeline_lines": 5})
        return queried[0] if queried else None

    def test_bare_mode_name_short_form(self, monkeypatch):
        assert self._queried_mode_name(monkeypatch, "# -*- python -*-") == "python"

    def test_mode_key_value_form(self, monkeypatch):
        assert self._queried_mode_name(monkeypatch, "# -*- mode: python -*-") == "python"

    def test_mode_key_first_among_multiple_vars(self, monkeypatch):
        """Regression: the old regex's greedy capture grabbed the whole "key: value; ..." list
        instead of just the mode name, so a syntax literally named "mode: python; coding: utf-8"
        was looked up (and never found) instead of "python"."""
        assert self._queried_mode_name(monkeypatch, "# -*- mode: python; coding: utf-8 -*-") == "python"

    def test_mode_key_last_among_multiple_vars(self, monkeypatch):
        assert self._queried_mode_name(monkeypatch, "# -*- coding: utf-8; mode: python -*-") == "python"

    def test_mode_keyword_is_case_insensitive(self, monkeypatch):
        assert self._queried_mode_name(monkeypatch, "# -*- Mode: Python -*-") == "Python"

    def test_no_mode_key_present_resolves_nothing(self, monkeypatch):
        """A "key: value" list with no "mode" key has no mode name to use -- must not fall back
        to treating the whole list (e.g. "coding: utf-8") as if it were one."""
        assert self._queried_mode_name(monkeypatch, "# -*- coding: utf-8 -*-") is None


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
        """same_buffer=True (the default) is meant to keep clones/split-views of the same buffer
        in sync -- a syntax change to one clone must apply to every view of that buffer."""
        old_syntax = sublime.Syntax(name="Plain Text")
        view1 = _make_view(syntax=old_syntax)
        view2 = _make_view(syntax=old_syntax)
        view1.buffer.return_value.views.return_value = [view1, view2]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view1, new_syntax) is True

        view1.assign_syntax.assert_called_once_with(new_syntax)
        view2.assign_syntax.assert_called_once_with(new_syntax)

    def test_same_buffer_false_only_touches_the_given_view(self):
        old_syntax = sublime.Syntax(name="Plain Text")
        view1 = _make_view(syntax=old_syntax)
        view2 = _make_view(syntax=old_syntax)
        view1.buffer.return_value.views.return_value = [view1, view2]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view1, new_syntax, same_buffer=False) is True

        view1.assign_syntax.assert_called_once_with(new_syntax)
        view2.assign_syntax.assert_not_called()

    def test_view_without_a_window_is_skipped(self):
        """A view that briefly has no window (e.g. mid-teardown) must be skipped, not crash.
        Documents current (accepted) behavior: the function still returns True even though
        nothing was actually assigned, since every candidate view lacked a window -- this only
        means run_auto_set_syntax_on_view() won't retry other strategies for *this* event; the
        view keeps whatever syntax it already had, and the next event re-evaluates it fresh."""
        old_syntax = sublime.Syntax(name="Plain Text")
        view = _make_view(syntax=old_syntax)
        view.window.return_value = None
        view.buffer.return_value.views.return_value = [view]
        new_syntax = sublime.Syntax(name="Python")

        assert mod.assign_syntax_to_view(view, new_syntax) is True
        view.assign_syntax.assert_not_called()


class TestAssignSyntaxWithTrimmedFilename:
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
        calls = []
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: calls.append(kw) or True)

        assert mod._assign_syntax_with_trimmed_filename(snap, ListenerEvent.SAVE, settings) is True
        assert calls[0]["details"]["filename_trimmed"] == "app.js"

    def test_no_matching_suffix_returns_false(self, monkeypatch):
        snap = self._make_snapshot_for_trimming("app.js")
        settings = {"trim_suffixes": (".min",), "trim_suffixes_auto": False}

        monkeypatch.setattr(mod.sublime, "find_syntax_for_file", lambda *a, **kw: None, raising=False)
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_trimmed_filename(snap, ListenerEvent.SAVE, settings) is False

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
        calls = []
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: calls.append(kw) or True)

        assert mod._assign_syntax_with_trimmed_filename(snap, ListenerEvent.SAVE, settings) is True
        assert calls[0]["details"]["filename_trimmed"] == "app.js"

    def test_non_plaintext_current_syntax_skips_entirely(self, monkeypatch):
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
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_trimmed_filename(snap, ListenerEvent.SAVE, {}) is False

    def test_unsaved_buffer_with_no_file_name_returns_false(self, monkeypatch):
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
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_trimmed_filename(snap, ListenerEvent.SAVE, {}) is False


class _FakeMagikaResult:
    def __init__(self, *, ok: bool = True, status: str = "", label: str = "python", score: float = 0.9) -> None:
        self.ok = ok
        self.status = status
        self.dl = MagicMock(label=label)
        self.score = score

    def __repr__(self) -> str:
        return f"<FakeMagikaResult label={self.dl.label} score={self.score}>"


class TestAssignSyntaxWithMagika:
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
        monkeypatch.setattr(mod.sublime, "status_message", lambda *a, **kw: None, raising=False)
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

        result = mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": False})

        assert result is False
        magika_obj.identify_path.assert_not_called()
        magika_obj.identify_bytes.assert_not_called()

    def test_happy_path_assigns_syntax(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()
        calls = []
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: calls.append(kw) or True)

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is True
        assert calls[0]["details"]["reason"] == "Magika (Deep Learning)"

    def test_score_below_threshold_returns_false(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.3)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()
        settings = {"magika.enabled": True, "magika.min_confidence": 0.5}

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, settings) is False

    def test_ignored_label_returns_false(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="txt", score=0.99)
        self._install_magika(monkeypatch, magika_obj)
        monkeypatch.setattr(mod, "get_magika_ignored_labels", lambda: {"txt"})
        snap = self._make_magika_snapshot()

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is False

    def test_failed_identification_returns_false(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(ok=False, status="error")
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot()

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is False

    def test_modify_event_single_line_content_skipped(self, monkeypatch):
        """Guards against reclassifying mid-typing on the very first line, e.g. right after
        typing "import" -- too early to tell Python from JS/TS."""
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(content="import ", dirty=True)

        result = mod._assign_syntax_with_magika(snap, ListenerEvent.MODIFY, {"magika.enabled": True})

        assert result is False
        magika_obj.identify_bytes.assert_not_called()

    def test_modify_event_multi_line_content_proceeds(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(content="import os\nprint(os.getcwd())\n", dirty=True)
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.MODIFY, {"magika.enabled": True}) is True

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

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is False
        magika_obj.identify_path.assert_not_called()

        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)
        assert mod._assign_syntax_with_magika(snap, ListenerEvent.COMMAND, {"magika.enabled": True}) is True

    def test_dirty_buffer_uses_identify_bytes_not_identify_path(self, monkeypatch):
        """A dirty (unsaved-changes) buffer's on-disk content is stale -- must analyze the live
        in-memory content instead of re-reading the (outdated) file from disk."""
        magika_obj = MagicMock()
        magika_obj.identify_bytes.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(dirty=True)
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is True
        magika_obj.identify_path.assert_not_called()
        magika_obj.identify_bytes.assert_called_once()

    def test_clean_buffer_with_path_uses_identify_path(self, monkeypatch):
        magika_obj = MagicMock()
        magika_obj.identify_path.return_value = _FakeMagikaResult(label="python", score=0.9)
        self._install_magika(monkeypatch, magika_obj)
        snap = self._make_magika_snapshot(dirty=False)
        monkeypatch.setattr(mod, "assign_syntax_to_view", lambda *a, **kw: True)

        assert mod._assign_syntax_with_magika(snap, ListenerEvent.LOAD, {"magika.enabled": True}) is True
        magika_obj.identify_bytes.assert_not_called()
        magika_obj.identify_path.assert_called_once()
