"""Tests for the scaffolded `.python-version` written by the create-new-implementation command."""

import sys


class TestPythonVersionShort:
    def test_matches_running_interpreter_major_minor(self):
        from plugin.commands.auto_set_syntax_create_new_implementation import _PYTHON_VERSION_SHORT

        assert f"{sys.version_info.major}.{sys.version_info.minor}" == _PYTHON_VERSION_SHORT
