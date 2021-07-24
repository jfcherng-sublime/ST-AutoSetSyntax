from ...helper import compile_regex
from ...helper import merge_literals_to_regex
from ..constraint import AbstractConstraint
from typing import Any, Tuple
import sublime


class IsInterpreterConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.interpretors: Tuple[str, ...] = self._handled_args()
        interpretor_names_regex = merge_literals_to_regex(self.interpretors)
        self.re_shebang = compile_regex(rf"^#!(?:.+)\b{interpretor_names_regex}\b")

    def is_droppable(self) -> bool:
        return not self.re_shebang

    def test(self, view: sublime.View) -> bool:
        return bool(self.re_shebang.search(self.get_view_info(view)["first_line"]))
