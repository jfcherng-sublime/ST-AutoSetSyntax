from ..constraint import AbstractConstraint
from typing import Any, Tuple
import sublime


class PathContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view: sublime.View) -> bool:
        filepath = self.get_view_info(view)["file_path"]
        return any((needle in filepath) for needle in self.needles)
