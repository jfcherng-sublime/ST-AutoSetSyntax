from __future__ import annotations

from typing import Any, Mapping

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, PY_VERSION, ST_CHANNEL, ST_PLATFORM_ARCH, ST_VERSION, VERSION
from ..rules.constraint import get_constraints
from ..rules.match import get_matches
from ..settings import get_merged_plugin_settings
from ..shared import G
from ..utils import find_syntax_by_syntax_like, get_fqcn, stringify

TEMPLATE = f"""
# === {PLUGIN_NAME} Debug Information === #
# You may use the following website to format this debug information.
# @link https://play.ruff.rs/?secondary=Format

###############
# Environment #
###############

{{env}}

###################
# Plugin settings #
###################

{{plugin_settings}}

##########################
# Syntax rule collection #
##########################

{{syntax_rule_collection}}

########################
# Dropped syntax rules #
########################

{{dropped_rules}}
""".lstrip()


def _pythonize(d: Mapping[str, Any]) -> dict[str, str]:
    return {k: stringify(v) for k, v in d.items()}


class AutoSetSyntaxDebugInformationCommand(sublime_plugin.WindowCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Debug Information"

    def run(self, *, copy_only: bool = False) -> None:
        info: dict[str, Any] = {}

        info["env"] = {
            "sublime_text": f"{ST_VERSION} ({ST_PLATFORM_ARCH} {ST_CHANNEL} build) with Python {PY_VERSION}",
            "plugin": {
                "version": VERSION,
                "matches": tuple(map(get_fqcn, get_matches())),
                "constraints": tuple(map(get_fqcn, get_constraints())),
            },
        }
        info["plugin_settings"] = get_merged_plugin_settings(window=self.window)
        info["syntax_rule_collection"] = G.syntax_rule_collections.get(self.window)
        info["dropped_rules"] = G.dropped_rules_collection.get(self.window, [])

        content = TEMPLATE.format_map(_pythonize(info))

        if copy_only:
            sublime.set_clipboard(content)
            sublime.message_dialog(f"{PLUGIN_NAME} debug information has been copied to the clipboard.")
            return

        view = self.window.new_file()
        view.set_name(f"{PLUGIN_NAME} Debug Information")
        view.set_scratch(True)
        view.run_command("append", {"characters": content})
        view.settings().update({
            "is_auto_set_syntax_template_buffer": True,
        })

        if syntax := find_syntax_by_syntax_like("scope:source.python"):
            view.assign_syntax(syntax)
