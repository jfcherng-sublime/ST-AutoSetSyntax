from __future__ import annotations

import math
import re
from contextlib import contextmanager
from typing import Any, Final, Generator

import sublime
import sublime_plugin

from .constants import PLUGIN_NAME
from .settings import get_merged_plugin_setting, get_st_setting
from .utils import resolve_window


@contextmanager
def _editable_view(view: sublime.View) -> Generator[sublime.View, None, None]:
    is_read_only = view.is_read_only()
    view.set_read_only(False)
    try:
        yield view
    finally:
        view.set_read_only(is_read_only)


def _find_log_panel(obj: Any) -> sublime.View | None:
    return (resolve_window(obj) or sublime.active_window()).find_output_panel(PLUGIN_NAME)


def _create_log_panel(window: sublime.Window) -> sublime.View:
    panel = window.create_output_panel(PLUGIN_NAME)
    # Somehow there is an error about "scope:output.autosetsyntax.log" not found during updating this plugin.
    # Thus, I change it to use the syntax path to load the syntax.
    panel.assign_syntax(Logger.SYNTAX_FILE)
    panel.set_read_only(True)
    panel.set_scratch(True)
    panel.settings().update({
        "draw_white_space": "none",
        "gutter": False,
        "is_widget": True,  # ST 3 convention for a non-normal view
        "line_numbers": False,
        "scroll_context_lines": 0,
        "scroll_past_end": False,
        "spell_check": False,
        "word_wrap": False,
    })
    return panel


class Logger:
    DELIMITER: Final[str] = "-" * 10
    SYNTAX_FILE: Final[str] = f"Packages/{PLUGIN_NAME}/syntaxes/AutoSetSyntaxLog.sublime-syntax"

    history_counts: dict[int, int] = {}
    """per-window, WindowId => history count"""

    @classmethod
    def log(cls, msg: str, *, window: sublime.Window | None = None, enabled: bool = True) -> None:
        window = window or sublime.active_window()
        if not (enabled and get_merged_plugin_setting("enable_log", window=window)):
            return

        max_lines = get_st_setting("console_max_history_lines", math.inf) / 8
        if cls._get_history_count(window) >= max_lines:
            cls.clear(window=window)

        window.run_command("auto_set_syntax_append_log", {"msg": msg})
        cls._increase_history_count(window)
        cls._clear_undo_stack(window)

    @classmethod
    def clear(cls, *, window: sublime.Window | None = None) -> None:
        window = window or sublime.active_window()
        window.run_command("auto_set_syntax_clear_log_panel", {"from_logger": True})
        cls._set_history_count(window, 0)
        cls._clear_undo_stack(window)

    @classmethod
    def destroy(cls, *, window: sublime.Window | None = None) -> None:
        window = window or sublime.active_window()
        window.destroy_output_panel(PLUGIN_NAME)
        cls.history_counts.pop(window.id(), None)

    @classmethod
    def _get_history_count(cls, window: sublime.Window) -> int:
        return cls.history_counts.get(window.id(), 0)

    @classmethod
    def _set_history_count(cls, window: sublime.Window, value: int) -> None:
        cls.history_counts[window.id()] = value

    @classmethod
    def _increase_history_count(cls, window: sublime.Window, amount: int = 1) -> None:
        cls._set_history_count(window, cls._get_history_count(window) + amount)

    @classmethod
    def _clear_undo_stack(cls, window: sublime.Window) -> None:
        if panel := _find_log_panel(window):
            sublime.set_timeout_async(panel.clear_undo_stack)


class AutoSetSyntaxUpdateLogCommand(sublime_plugin.TextCommand):
    """Internal use only."""

    def is_visible(self) -> bool:
        return False

    def run(self, edit: sublime.Edit, region: list[int], msg: str) -> None:
        with _editable_view(self.view):
            self.view.replace(edit, sublime.Region(*region), msg)


class AutoSetSyntaxAppendLogCommand(sublime_plugin.WindowCommand):
    """Internal use only."""

    def is_visible(self) -> bool:
        return False

    def run(self, msg: str, squash_history: bool = True) -> None:
        if not (panel := _find_log_panel(self.window)):
            panel = _create_log_panel(self.window)

        if (
            squash_history
            and (last_line_region := panel.full_line(panel.size() - 1))
            and (last_line := panel.substr(last_line_region).rstrip()).startswith(msg)
            and (m := re.match(r"(?: +\(x(\d+)\))?", last_line[len(msg) :]))
        ):
            msg = f"{msg} (x{int(m.group(1) or 1) + 1})"
            replace_region = last_line_region
        else:
            replace_region = sublime.Region(panel.size())  # EOF

        panel.run_command("auto_set_syntax_update_log", {"region": replace_region.to_tuple(), "msg": f"{msg}\n"})


class AutoSetSyntaxClearLogPanelCommand(sublime_plugin.WindowCommand):
    """Clear the plugin log panel for the current window."""

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Clear Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.window))

    def run(self, *, from_logger: bool = False) -> None:
        # ensure command is triggered by the logger so that we can maintain internal states
        if not from_logger:
            Logger.clear(window=self.window)
            return

        if panel := _find_log_panel(self.window):
            panel.run_command("auto_set_syntax_update_log", {"region": (0, panel.size()), "msg": ""})


class AutoSetSyntaxToggleLogPanelCommand(sublime_plugin.WindowCommand):
    """Toggle the visibility of the plugin log panel for the current window."""

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Toggle Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.window))

    def run(self) -> None:
        self.window.run_command("show_panel", {"panel": f"output.{PLUGIN_NAME}", "toggle": True})
