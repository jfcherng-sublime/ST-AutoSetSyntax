from .compatibility import view_clear_undo_stack
from .constant import PLUGIN_NAME
from .helper import get_st_window
from .settings import get_merged_plugin_setting
from .settings import get_st_setting
from typing import Dict, Optional, Union
import math
import sublime
import sublime_plugin


def _find_log_panel(obj: Union[sublime.View, sublime.Window]) -> Optional[sublime.View]:
    window = get_st_window(obj)
    return window.find_output_panel(PLUGIN_NAME) if window else None


def _create_log_panel(window: sublime.Window) -> sublime.View:
    panel = window.create_output_panel(PLUGIN_NAME)
    # Somehow there is an error about "scope:output.autosetsyntax.log" not found during updating this plugin.
    # Thus, I change it to use the syntax path to load the syntax.
    panel.assign_syntax("Packages/AutoSetSyntax/syntaxes/AutoSetSyntaxLog.sublime-syntax")
    panel.set_scratch(True)
    panel.settings().update(
        {
            "command_mode": True,  # user read-only but plugin API writable
            "draw_white_space": "none",
            "gutter": False,
            "line_numbers": False,
            "scroll_past_end": False,
            "spell_check": False,
            "word_wrap": False,
        }
    )
    return panel


class Logger:
    # per-window, WindowId => history count
    history_counts: Dict[int, int] = {}

    @classmethod
    def log(
        cls,
        window: Optional[sublime.Window],
        msg: str,
        show_plugin_name: bool = True,
        enabled: bool = True,
    ) -> None:
        if not (enabled and window and get_merged_plugin_setting(window, "enable_log")):
            return

        if cls._get_history_count(window) >= get_st_setting("console_max_history_lines", math.inf):
            cls.clear(window)

        window.run_command(
            "auto_set_syntax_append_log",
            {
                "msg": f"[{PLUGIN_NAME}] {msg}" if show_plugin_name else msg,
            },
        )
        cls._increase_history_count(window)
        cls._clear_undo_stack(window)

    @classmethod
    def clear(cls, window: Optional[sublime.Window]) -> None:
        if window:
            window.run_command("auto_set_syntax_clear_log_panel")
            cls._set_history_count(window, 0)
            cls._clear_undo_stack(window)

    @classmethod
    def destroy(cls, window: sublime.Window) -> None:
        window.destroy_output_panel(PLUGIN_NAME)
        cls.history_counts.pop(window.id())

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
            view_clear_undo_stack(panel)


class AutoSetSyntaxAppendLogCommand(sublime_plugin.TextCommand):
    """Internal use only."""

    def is_visible(self) -> bool:
        return False

    def run(self, edit: sublime.Edit, msg: str) -> None:
        if not (window := self.view.window()):
            return

        if not (panel := _find_log_panel(window)):
            panel = _create_log_panel(window)

        panel.insert(edit, panel.size(), f"{msg}\n")


class AutoSetSyntaxClearLogPanelCommand(sublime_plugin.TextCommand):
    """Clear the plugin log panel for the current window."""

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Clear Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.view))

    def run(self, edit: sublime.Edit) -> None:
        if panel := _find_log_panel(self.view):
            panel.erase(edit, sublime.Region(0, panel.size()))


class AutoSetSyntaxToggleLogPanelCommand(sublime_plugin.WindowCommand):
    """Toggle the visibility of the plugin log panel for the current window."""

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Toggle Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.window))

    def run(self) -> None:
        self.window.run_command(
            "show_panel",
            {
                "panel": f"output.{PLUGIN_NAME}",
                "toggle": True,
            },
        )
