from typing import Any, Pattern, Tuple, final

import sublime

from ...helper import compile_regex, merge_literals_to_regex, merge_regexes
from ..constraint import AbstractConstraint


@final
class IsInterpreterConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.interpretors: Tuple[str, ...] = self._handled_args()
        syntax_regex = merge_literals_to_regex(self.interpretors)
        self.first_line_regex: Pattern[str] = compile_regex(
            merge_regexes(
                (
                    # shebang
                    rf"^#!(?:.+)\b{syntax_regex}\b",
                    # VIM's syntax line
                    rf"\bsyntax={syntax_regex}(?=$|\\s)",
                )
            )
        )

    def is_droppable(self) -> bool:
        return not self.first_line_regex

    def test(self, view: sublime.View) -> bool:
        return bool(self.first_line_regex.search(self.get_view_snapshot(view).first_line))
