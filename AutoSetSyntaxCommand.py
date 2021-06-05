import sublime
import sublime_plugin
from .functions import view_assign_syntax
from .Globals import Globals
from .settings import get_setting


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> bool:
        """match the first line and set the corresponding syntax"""

        # make sure the target view is not a panel
        if not Globals.syntax_mappings:
            Globals.logger.info('Plugin is not ready yet. Wait a second.')
            return False

        # make sure the target view is not a panel
        if self.view.settings().get("is_widget"):
            return False

        first_line = self._get_partial_first_line()

        for syntax_mapping in Globals.syntax_mappings:
            for first_line_match_regex in syntax_mapping["first_line_match_compiled"]:
                # "first_line_match_regex" may be None if its corresponding regex is not compile-able
                if not first_line_match_regex:
                    continue

                if first_line_match_regex.search(first_line):
                    view_assign_syntax(
                        self.view,
                        syntax_mapping["file_path"],
                        '({rule_source}) "first_line_match": {regex}'.format(
                            rule_source=syntax_mapping["rule_source"],
                            regex=first_line_match_regex.pattern,
                        ),
                    )

                    return True

        return False

    def _get_partial_first_line(self) -> str:
        """get the (partial) first line"""

        max_length = get_setting("first_line_length_max")  # type: int
        if max_length >= 0:
            return self.view.substr(sublime.Region(0, max_length)).split("\n", 1)[0]

        return self.view.substr(self.view.line(0))
