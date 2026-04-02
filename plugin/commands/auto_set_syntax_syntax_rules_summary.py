from collections import defaultdict
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..helpers import create_new_view
from ..shared import G
from ..types import StSyntaxRule


class AutoSetSyntaxSyntaxRulesSummaryCommand(sublime_plugin.WindowCommand):
    @override
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Syntax Rules Summary"

    @override
    def run(self) -> None:
        if not (rule_collection := G.syntax_rule_collections.get(self.window)):
            return

        summary: defaultdict[sublime.Syntax, list[StSyntaxRule]] = defaultdict(list)
        for rule in rule_collection.rules:
            if rule.syntax and rule.src_setting:
                summary[rule.syntax].append(rule.src_setting)

        content = f"// [{PLUGIN_NAME}] Syntax Rules Summary\n\n"
        for syntax, rules in sorted(summary.items(), key=lambda x: x[0].name.casefold()):
            content += "/" * 80 + f"\n// Syntax: {syntax.name}\n" + "/" * 80 + "\n\n"
            content += "\n".join(st_rule.model_dump_json(indent=4) for st_rule in rules) + "\n\n"

        create_new_view(
            name=self.description(),
            content=content,
            syntax="scope:source.autosetsyntax.jsonc",
            include_hidden_syntax=True,
            scratch=True,
            window=self.window,
        )
