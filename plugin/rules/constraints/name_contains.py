from typing import Any, Tuple, final

import sublime

from ..constraint import AbstractConstraint


@final
class NameContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view: sublime.View) -> bool:
        filename = self.get_view_info(view)["file_name"]
        return any((needle in filename) for needle in self.needles)
