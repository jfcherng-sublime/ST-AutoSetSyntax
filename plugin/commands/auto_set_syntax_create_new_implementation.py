from __future__ import annotations

from abc import ABC
from pathlib import Path

import sublime
import sublime_plugin

from ..constants import PLUGIN_CUSTOM_DIR, PLUGIN_CUSTOM_MODULE_PATHS, PLUGIN_NAME, VIEW_KEY_IS_CREATED
from ..types import SyntaxLike
from ..utils import find_syntax_by_syntax_like


class AbstractCreateNewImplementationCommand(ABC, sublime_plugin.WindowCommand):
    template_type = ""
    template_file = ""
    template_syntax: str | None = None
    save_dir = ""

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Create New {self.template_type}"

    def run(self) -> None:
        if not _clone_file_as_template(
            self.window,
            f"Packages/{PLUGIN_NAME}/templates/{self.template_file}",
            self.save_dir,
            self.template_syntax,
        ):
            return

        save_dir = Path(self.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        (PLUGIN_CUSTOM_DIR / ".python-version").write_text("3.8\n", encoding="utf-8")


class AutoSetSyntaxCreateNewConstraintCommand(AbstractCreateNewImplementationCommand):
    template_type = "Constraint"
    template_file = "example_constraint.py"
    template_syntax = "scope:source.python"
    save_dir = str(PLUGIN_CUSTOM_MODULE_PATHS["constraint"])


class AutoSetSyntaxCreateNewMatchCommand(AbstractCreateNewImplementationCommand):
    template_type = "Match"
    template_file = "example_match.py"
    template_syntax = "scope:source.python"
    save_dir = str(PLUGIN_CUSTOM_MODULE_PATHS["match"])


def _clone_file_as_template(
    window: sublime.Window,
    source_path: str,
    save_dir: str,
    syntax: SyntaxLike | None = None,
) -> sublime.View | None:
    try:
        template = sublime.load_resource(source_path)
    except FileNotFoundError as e:
        sublime.error_message(str(e))
        return None

    new = window.new_file()
    new.run_command("append", {"characters": template})
    new.settings().update({
        "default_dir": save_dir,
        VIEW_KEY_IS_CREATED: True,
    })

    if syntax and (syntax := find_syntax_by_syntax_like(syntax)):
        new.assign_syntax(syntax)

    return new
