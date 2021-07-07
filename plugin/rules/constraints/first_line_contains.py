from ..constraint import AbstractConstraint
from typing import Any, Tuple
import sublime


class FirstLineContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = tuple(filter(None, self.args))

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view: sublime.View) -> bool:
        first_line = self.get_view_info(view)["first_line"]
        return any((needle in first_line) for needle in self.needles)
