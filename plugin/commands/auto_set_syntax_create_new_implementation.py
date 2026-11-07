import sys
from abc import ABC
from pathlib import Path
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_CUSTOM_DIR
from ..constants import PLUGIN_CUSTOM_MODULE_PATHS
from ..constants import PLUGIN_NAME
from ..helpers import create_new_view

_PYTHON_VERSION_SHORT = f"{sys.version_info.major}.{sys.version_info.minor}"
"""The running interpreter's `major.minor` version, for the scaffolded `.python-version` file."""


class AbstractCreateNewImplementationCommand(ABC, sublime_plugin.WindowCommand):
    template_type = ""
    template_file = ""
    template_syntax = "scope:source.python"
    save_dir = ""

    @override
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Create New {self.template_type}"

    @override
    def run(self) -> None:
        source_path = f"Packages/{PLUGIN_NAME}/templates/{self.template_file}"
        try:
            template = sublime.load_resource(source_path)
        except FileNotFoundError as e:
            sublime.error_message(str(e))
            return

        create_new_view(
            content=template,
            syntax=self.template_syntax,
            settings={"default_dir": self.save_dir},
            window=self.window,
        )

        save_dir = Path(self.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        (PLUGIN_CUSTOM_DIR / ".python-version").write_text(f"{_PYTHON_VERSION_SHORT}\n", encoding="utf-8")


class AutoSetSyntaxCreateNewConstraintCommand(AbstractCreateNewImplementationCommand):
    template_type = "Constraint"
    template_file = "example_constraint.py"
    save_dir = str(PLUGIN_CUSTOM_MODULE_PATHS["constraint"])


class AutoSetSyntaxCreateNewMatchCommand(AbstractCreateNewImplementationCommand):
    template_type = "Match"
    template_file = "example_match.py"
    save_dir = str(PLUGIN_CUSTOM_MODULE_PATHS["match"])
