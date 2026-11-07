"""Tests for AutoSetSyntaxAppendLogCommand's history-squashing logic and Logger's public API."""

import math
from contextlib import suppress
from unittest.mock import MagicMock

import sublime

import plugin.logger as logger_mod
from plugin.logger import AutoSetSyntaxAppendLogCommand
from plugin.logger import AutoSetSyntaxClearLogPanelCommand
from plugin.logger import AutoSetSyntaxToggleLogPanelCommand
from plugin.logger import AutoSetSyntaxUpdateLogCommand
from plugin.logger import Logger


def _make_window_with_panel(*, last_line: str, panel_size: int = 100):
    panel = MagicMock()
    panel.size.return_value = panel_size
    panel.full_line.return_value = sublime.Region(panel_size - len(last_line), panel_size)
    panel.substr.return_value = last_line
    panel.run_command = MagicMock()

    window = sublime.Window()
    window.find_output_panel = MagicMock(return_value=panel)
    return window, panel


class TestAppendLogSquashing:
    def test_exact_repeat_is_squashed_with_counter(self):
        window, panel = _make_window_with_panel(last_line="Hello")

        AutoSetSyntaxAppendLogCommand(window).run(msg="Hello")

        args, _ = panel.run_command.call_args
        assert args[1]["msg"] == "Hello (x2)\n"

    def test_repeated_repeat_increments_existing_counter(self):
        window, panel = _make_window_with_panel(last_line="Hello (x2)")

        AutoSetSyntaxAppendLogCommand(window).run(msg="Hello")

        args, _ = panel.run_command.call_args
        assert args[1]["msg"] == "Hello (x3)\n"

    def test_message_that_is_a_prefix_of_last_line_is_not_squashed(self):
        """A distinct new message must not be mistaken for a repeat just because it's a string
        prefix of the previous (different) line -- only an exact repeat or a "(xN)" suffix
        should trigger squashing."""
        window, panel = _make_window_with_panel(last_line="Hello World")

        AutoSetSyntaxAppendLogCommand(window).run(msg="Hello")

        args, _ = panel.run_command.call_args
        assert args[1]["msg"] == "Hello\n"
        assert args[1]["region"] == (100, 100)  # appended at EOF, not squashed into the last line


def _make_window(window_id: int = 42) -> sublime.Window:
    window = sublime.Window()
    window.id = MagicMock(return_value=window_id)
    window.run_command = MagicMock()
    window.find_output_panel = MagicMock(return_value=None)
    window.destroy_output_panel = MagicMock()
    return window


class TestLoggerLog:
    def setup_method(self):
        Logger.history_counts.clear()

    def test_noop_when_logging_disabled_by_setting(self, monkeypatch):
        monkeypatch.setattr(logger_mod, "get_merged_plugin_setting", lambda *a, **kw: False)
        window = _make_window()

        Logger.log("hello", window=window)

        window.run_command.assert_not_called()

    def test_callable_message_not_evaluated_when_logging_disabled(self, monkeypatch):
        """Lazy messages (e.g. `lambda: expensive_stringify(...)`) must not be evaluated at all
        when logging is off -- that's the whole point of allowing a callable."""
        monkeypatch.setattr(logger_mod, "get_merged_plugin_setting", lambda *a, **kw: False)
        window = _make_window()
        calls = []

        Logger.log(lambda: calls.append(1) or "hello", window=window)

        assert calls == []

    def test_appends_the_message(self, monkeypatch):
        monkeypatch.setattr(logger_mod, "get_merged_plugin_setting", lambda *a, **kw: True)
        monkeypatch.setattr(logger_mod, "get_st_setting", lambda *a, **kw: math.inf)
        window = _make_window()

        Logger.log("hello", window=window)

        window.run_command.assert_called_once_with("auto_set_syntax_append_log", {"msg": "hello"})

    def _logged_commands(self, monkeypatch, *, already_logged: int) -> list[str]:
        """Log once with `console_max_history_lines` at 16 (so the panel holds 2 messages)."""
        monkeypatch.setattr(logger_mod, "get_merged_plugin_setting", lambda *a, **kw: True)
        monkeypatch.setattr(logger_mod, "get_st_setting", lambda *a, **kw: 16)
        window = _make_window()
        for _ in range(already_logged):
            Logger.log("earlier", window=window)
        window.run_command.reset_mock()
        # a real window would run the command, which is what resets the count
        window.run_command.side_effect = lambda name, *a: (
            AutoSetSyntaxClearLogPanelCommand(window).run() if name == "auto_set_syntax_clear_log_panel" else None
        )

        Logger.log("hello", window=window)

        return [c.args[0] for c in window.run_command.call_args_list]

    def test_a_full_panel_is_cleared_before_the_new_message_is_appended(self, monkeypatch):
        calls = self._logged_commands(monkeypatch, already_logged=2)

        assert calls == ["auto_set_syntax_clear_log_panel", "auto_set_syntax_append_log"]

    def test_a_panel_with_room_is_not_cleared(self, monkeypatch):
        calls = self._logged_commands(monkeypatch, already_logged=1)

        assert calls == ["auto_set_syntax_append_log"]

    def test_the_count_starts_over_after_a_clear(self, monkeypatch):
        self._logged_commands(monkeypatch, already_logged=2)  # cleared, then logged once

        calls = self._logged_commands(monkeypatch, already_logged=0)
        assert calls == ["auto_set_syntax_append_log"]


class TestLoggerClearAndDestroy:
    def setup_method(self):
        Logger.history_counts.clear()

    def test_clear_runs_the_clear_command(self):
        window = _make_window()

        Logger.clear(window=window)

        window.run_command.assert_called_once_with("auto_set_syntax_clear_log_panel")

    def test_destroy_removes_the_panel_and_forgets_its_count(self):
        window = _make_window()
        Logger.history_counts[window.id()] = 5

        Logger.destroy(window=window)

        window.destroy_output_panel.assert_called_once()
        assert window.id() not in Logger.history_counts


class TestAutoSetSyntaxUpdateLogCommand:
    def test_replaces_region_while_temporarily_editable(self):
        view = MagicMock()
        view.is_read_only.return_value = True
        edit = MagicMock()

        AutoSetSyntaxUpdateLogCommand(view).run(edit, region=[0, 5], msg="hi")

        view.set_read_only.assert_any_call(False)
        view.replace.assert_called_once()
        # restored to the original read-only state afterward
        assert view.set_read_only.call_args_list[-1].args == (True,)

    def test_restores_read_only_state_even_if_replace_raises(self):
        view = MagicMock()
        view.is_read_only.return_value = False
        view.replace.side_effect = RuntimeError("boom")
        edit = MagicMock()

        with suppress(RuntimeError):
            AutoSetSyntaxUpdateLogCommand(view).run(edit, region=[0, 5], msg="hi")

        assert view.set_read_only.call_args_list[-1].args == (False,)


class TestAutoSetSyntaxClearLogPanelCommand:
    def test_empties_the_panel_and_resets_the_count(self):
        window = _make_window()
        panel = MagicMock()
        panel.size.return_value = 123
        window.find_output_panel.return_value = panel
        Logger.history_counts[window.id()] = 5

        AutoSetSyntaxClearLogPanelCommand(window).run()

        panel.run_command.assert_called_once_with("auto_set_syntax_update_log", {"region": (0, 123), "msg": ""})
        assert window.id() not in Logger.history_counts

    def test_without_a_panel_it_only_resets_the_count(self):
        window = _make_window()
        Logger.history_counts[window.id()] = 5

        AutoSetSyntaxClearLogPanelCommand(window).run()  # must not raise

        assert window.id() not in Logger.history_counts

    def test_is_enabled_reflects_panel_existence(self):
        window = _make_window()
        window.find_output_panel.return_value = None
        assert AutoSetSyntaxClearLogPanelCommand(window).is_enabled() is False

        window.find_output_panel.return_value = MagicMock()
        assert AutoSetSyntaxClearLogPanelCommand(window).is_enabled() is True


class TestAutoSetSyntaxToggleLogPanelCommand:
    def test_run_toggles_the_output_panel(self):
        window = _make_window()

        AutoSetSyntaxToggleLogPanelCommand(window).run()

        window.run_command.assert_called_once_with(
            "show_panel", {"panel": f"output.{logger_mod.PLUGIN_NAME}", "toggle": True}
        )

    def test_is_enabled_reflects_panel_existence(self):
        window = _make_window()
        window.find_output_panel.return_value = None
        assert AutoSetSyntaxToggleLogPanelCommand(window).is_enabled() is False

        window.find_output_panel.return_value = MagicMock()
        assert AutoSetSyntaxToggleLogPanelCommand(window).is_enabled() is True
