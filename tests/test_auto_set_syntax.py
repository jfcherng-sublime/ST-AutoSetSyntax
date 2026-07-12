"""Tests for the syntax-assignment strategies in plugin/commands/auto_set_syntax.py.

This module is the plugin's core dispatch logic but previously had zero dedicated test
coverage (0% per `make ci-test-cov`), unlike almost everything else in the codebase.
"""

import sys

import sublime

import plugin.commands.auto_set_syntax as mod
from plugin.snapshot import ViewSnapshot
from plugin.types import ListenerEvent

MockView = sys.modules["sublime"].View


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
