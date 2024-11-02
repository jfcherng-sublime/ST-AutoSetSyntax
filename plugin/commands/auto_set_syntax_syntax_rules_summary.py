from __future__ import annotations

from collections import defaultdict

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, VIEW_KEY_IS_CREATED
from ..rules import SyntaxRule
from ..shared import G
from ..utils import find_syntax_by_syntax_like, stringify

TEMPLATE = f"""
# === [{PLUGIN_NAME}] Syntax Rules Summary === #
# You may use the following website to beautify this debug information.
# @link https://play.ruff.rs/?secondary=Format

########################
# Syntax Rules Summary #
########################

{{content}}
""".lstrip()


class AutoSetSyntaxSyntaxRulesSummaryCommand(sublime_plugin.WindowCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Syntax Rules Summary"

    def run(self, *, copy_only: bool = False) -> None:
        if not (rule_collection := G.syntax_rule_collections.get(self.window)):
            return

        summary: defaultdict[sublime.Syntax, list[SyntaxRule]] = defaultdict(list)
        for rule in rule_collection.rules:
            if rule.syntax:
                summary[rule.syntax].append(rule)

        content = ""
        for syntax_, rules in sorted(summary.items(), key=lambda x: x[0].name.casefold()):
            content += f"# Syntax: {syntax_.name}\n"
            for rule in rules:
                content += f"{stringify(rule)}\n"
            content += "\n"
        content = TEMPLATE.format(content=content)

        if copy_only:
            sublime.set_clipboard(content)
            sublime.message_dialog(f"[{PLUGIN_NAME}] The result has been copied to the clipboard.")
            return

        view = self.window.new_file()
        view.set_name(self.description())
        view.set_scratch(True)
        view.run_command("append", {"characters": content})
        view.settings().update({
            VIEW_KEY_IS_CREATED: True,
        })

        if syntax := find_syntax_by_syntax_like("scope:source.python"):
            view.assign_syntax(syntax)
