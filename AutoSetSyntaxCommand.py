import sublime
import sublime_plugin
from .Globals import Globals
from .settings import get_setting


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
        """ match the first line and set the corresponding syntax """

        view = self.view

        # make sure the target view is not a panel
        if view.settings().get("is_widget"):
            return

        first_line = self._get_partial_first_line()

        for syntax_mapping in Globals.syntax_mappings:
            syntax_file = syntax_mapping["file_path"]
            first_line_match_regexes = syntax_mapping["first_line_match_compiled"]

            if first_line_match_regexes is None:
                continue

            for first_line_match_regex in first_line_match_regexes:
                if first_line_match_regex.search(first_line) is not None:
                    view.assign_syntax(syntax_file)
                    Globals.logger.info(
                        'Assign syntax to "{0}" due to: {1}'.format(
                            syntax_file, first_line_match_regex.pattern
                        )
                    )

                    return

    def _get_partial_first_line(self) -> str:
        """ get the (partial) first line """

        view = self.view
        region = view.line(0)
        first_line_length_max = get_setting("first_line_length_max")

        if first_line_length_max >= 0:
            # if the first line is longer than the max line length,
            # then we use the max line length
            region = sublime.Region(0, min(region.end(), first_line_length_max))

        return view.substr(region)
