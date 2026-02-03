from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

import sublime_plugin

from ..constants import PLUGIN_NAME, PY_VERSION, ST_CHANNEL, ST_PLATFORM_ARCH, ST_VERSION, VERSION
from ..helpers import create_new_view
from ..rules.constraint import get_constraints
from ..rules.match import get_matches
from ..settings import get_merged_plugin_settings
from ..shared import G
from ..utils import get_fqcn, stringify

TEMPLATE = f"""
# === [{PLUGIN_NAME}] Debug Information === #
# You may use the following website to beautify this debug information.
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
    @override
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Debug Information"

    @override
    def run(self) -> None:
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

        create_new_view(
            name=self.description(),
            content=content,
            syntax="scope:source.python",
            scratch=True,
            window=self.window,
        )
