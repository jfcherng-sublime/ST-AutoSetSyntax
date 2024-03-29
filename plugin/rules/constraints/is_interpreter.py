from __future__ import annotations

from typing import Any, Pattern, final

from ...snapshot import ViewSnapshot
from ...utils import compile_regex, merge_literals_to_regex, merge_regexes
from ..constraint import AbstractConstraint


@final
class IsInterpreterConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.interpreters: tuple[str, ...] = self._handled_args()
        self.loosy_version = bool(self.kwargs.get("loosy_version", False))

        interpreters_regex = merge_literals_to_regex(self.interpreters)
        if self.loosy_version:
            interpreters_regex = rf"(?:{interpreters_regex}(?:[\-_]?\d+(?:\.\d+)*)?)"

        self.first_line_regex: Pattern[str] = compile_regex(
            merge_regexes((
                # shebang
                rf"^#!(?:.+)\b{interpreters_regex}\b",
                # VIM's syntax line
                rf"\bsyntax={interpreters_regex}(?=$|\\s)",
            ))
        )

    def is_droppable(self) -> bool:
        return not self.first_line_regex

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return bool(self.first_line_regex.search(view_snapshot.first_line))
