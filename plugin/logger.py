from .compatibility import view_clear_undo_stack
from .constant import PLUGIN_NAME
from .helper import get_st_window
from .settings import get_merged_plugin_setting
from .settings import get_st_setting
from contextlib import contextmanager
from typing import Dict, Generator, Optional, Union
import math
import sublime
import sublime_plugin


def _check_log_panel(obj: Union[sublime.View, sublime.Window]) -> bool:
    window = get_st_window(obj)
    return bool(window.find_output_panel(PLUGIN_NAME) if window else None)


@contextmanager
def _find_log_panel(obj: Union[sublime.View, sublime.Window]) -> Generator[Optional[sublime.View], None, None]:
    window = get_st_window(obj)
    panel = window.find_output_panel(PLUGIN_NAME) if window else None
    try:
        yield panel
    finally:
        if panel:
            view_clear_undo_stack(panel)


def _create_log_panel(window: sublime.Window) -> sublime.View:
    panel = window.create_output_panel(PLUGIN_NAME)
    panel.assign_syntax("scope:output.autosetsyntax.log")
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
        cls._increment_history_count(window)

    @classmethod
    def clear(cls, window: Optional[sublime.Window]) -> None:
        if window:
            window.run_command("auto_set_syntax_clear_log_panel")
            cls._set_history_count(window, 0)

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
    def _increment_history_count(cls, window: sublime.Window, step: int = 1) -> None:
        cls._set_history_count(window, cls._get_history_count(window) + step)


class AutoSetSyntaxAppendLogCommand(sublime_plugin.TextCommand):
    """Internal use only."""

    def is_visible(self) -> bool:
        return False

    def run(self, edit: sublime.Edit, msg: str) -> None:
        if not (window := self.view.window()):
            return

        with _find_log_panel(window) as panel:
            if not panel:
                panel = _create_log_panel(window)
            panel.insert(edit, panel.size(), f"{msg}\n")


class AutoSetSyntaxClearLogPanelCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Clear Log Panel"

    def is_enabled(self) -> bool:
        return _check_log_panel(self.view)

    def is_visible(self) -> bool:
        return False

    def run(self, edit: sublime.Edit) -> None:
        with _find_log_panel(self.view) as panel:
            if panel:
                panel.erase(edit, sublime.Region(0, panel.size()))
                view_clear_undo_stack(panel)


class AutoSetSyntaxToggleLogPanelCommand(sublime_plugin.WindowCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Toggle Log Panel"

    def is_enabled(self) -> bool:
        return _check_log_panel(self.window)

    def is_visible(self) -> bool:
        return False

    def run(self) -> None:
        self.window.run_command(
            "show_panel",
            {
                "panel": f"output.{PLUGIN_NAME}",
                "toggle": True,
            },
        )
