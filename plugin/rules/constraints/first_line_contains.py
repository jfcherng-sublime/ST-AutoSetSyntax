from __future__ import annotations

from typing import Any, Tuple, final

import sublime

from ..constraint import AbstractConstraint


@final
class FirstLineContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view: sublime.View) -> bool:
        first_line = self.get_view_snapshot(view).first_line
        return any((needle in first_line) for needle in self.needles)
