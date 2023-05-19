from __future__ import annotations

from typing import Any, Tuple, final

import sublime

from ...utils import nth, str_finditer
from ..constraint import AbstractConstraint


@final
class ContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()
        self.threshold: int = kwargs.get("threshold", 1)

    def is_droppable(self) -> bool:
        return not (self.needles and isinstance(self.threshold, (int, float)))

    def test(self, view: sublime.View) -> bool:
        if self.threshold <= 0:
            return True

        content = self.get_view_snapshot(view).content

        return (
            nth(
                (_ for needle in self.needles for _ in str_finditer(content, needle)),
                self.threshold - 1,
            )
            is not None
        )
