from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class PathContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("file not on disk")

        return any((needle in file_path) for needle in self.needles)
