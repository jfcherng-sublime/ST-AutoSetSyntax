from ..constant import PLUGIN_NAME
from typing import Any, Dict, List, Union
import sublime
import sublime_plugin


class AutoSetSyntaxMigrateSettingsCommand(sublime_plugin.TextCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Migrates Plugin Settings"

    def run(self, edit: sublime.Edit) -> None:
        try:
            settings = sublime.decode_value(self.view.substr(sublime.Region(0, self.view.size())))
        except ValueError as e:
            sublime.error_message(f"Failed parsing View content: {e}")
            return

        if not (window := self.view.window()):
            return

        settings_new_json = sublime.encode_value(migrate_v1_to_v2(settings), pretty=True)
        settings_new_json = f"// Migrated AutoSetSyntax v2 settings from v1\n{settings_new_json}"

        view = window.new_file()
        view.set_scratch(True)
        view.set_name("NEW AutoSetSyntax settings")
        view.assign_syntax("scope:source.json")
        view.replace(edit, sublime.Region(0, view.size()), settings_new_json)

        sublime.message_dialog("Please update your settings with this one.")


def migrate_v1_to_v2(settings: Dict[str, Any]) -> Dict[str, Any]:
    def is_settings_v1(settings: Union[Dict[str, Any], sublime.Settings]) -> bool:
        return "syntax_mapping" in settings

    if not is_settings_v1(settings):
        return settings

    new: Dict[str, Any] = {}

    # ----------------------------- #
    # migrate first_line_length_max #
    # ----------------------------- #

    if (first_line_length_max := settings.get("first_line_length_max")) is not None:
        new["trim_first_line_length"] = first_line_length_max

    # -------------------------------- #
    # migrate try_filename_remove_exts #
    # -------------------------------- #

    if (try_filename_remove_exts := settings.get("try_filename_remove_exts")) is not None:
        new["user_trim_suffixes"] = try_filename_remove_exts

    # --------------------- #
    # migrate working_scope #
    # --------------------- #

    working_scope = "text.plain"  # I guess we can't migrate this as its a regex in v1

    # ---------------------- #
    # migrate syntax_mapping #
    # ---------------------- #

    user_syntax_rules: List[Dict[str, Any]] = []
    syntax_mapping: Dict[str, List[str]] = settings.get("syntax_mapping", {})
    for syntax, first_line_matches in syntax_mapping.items():
        user_syntax_rules.append(
            {
                "assign_syntaxes": [syntax],
                "selector": working_scope,
                "match": "any",
                "rules": [
                    {
                        "constraint": "first_line_contains_regexes",
                        "args": first_line_matches,
                    },
                ],
            }
        )
    new["user_syntax_rules"] = user_syntax_rules

    return new
