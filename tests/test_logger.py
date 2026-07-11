"""Tests for AutoSetSyntaxAppendLogCommand's history-squashing logic."""

from unittest.mock import MagicMock

import sublime

from plugin.logger import AutoSetSyntaxAppendLogCommand


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
