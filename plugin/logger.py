from .constant import PLUGIN_NAME
from .settings import get_merged_plugin_setting
from .settings import get_st_setting
from typing import Dict, Optional, Union
import math
import sublime
import sublime_plugin


def _find_log_panel(view_or_window: Union[sublime.View, sublime.Window]) -> Optional[sublime.View]:
    if isinstance(view_or_window, sublime.View):
        window = view_or_window.window()
    else:
        window = view_or_window

    return window.find_output_panel(PLUGIN_NAME) if window else None


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

        if not (panel := _find_log_panel(window)):
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

        panel.insert(edit, panel.size(), f"{msg}\n")


class AutoSetSyntaxClearLogPanelCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Clear Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.view))

    def is_visible(self) -> bool:
        return self.is_enabled()

    def run(self, edit: sublime.Edit) -> None:
        panel = _find_log_panel(self.view)
        assert panel  # guaranteed by is_enabled()
        panel.erase(edit, sublime.Region(0, panel.size()))


class AutoSetSyntaxToggleLogPanelCommand(sublime_plugin.WindowCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Toggle Log Panel"

    def is_enabled(self) -> bool:
        return bool(_find_log_panel(self.window))

    def is_visible(self) -> bool:
        return self.is_enabled()

    def run(self) -> None:
        self.window.run_command(
            "show_panel",
            {
                "panel": f"output.{PLUGIN_NAME}",
                "toggle": True,
            },
        )
