from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class FirstLineContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return any((needle in view_snapshot.first_line) for needle in self.needles)
