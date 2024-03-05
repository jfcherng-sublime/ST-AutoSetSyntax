from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsNameConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        names: tuple[str, ...] = self._handled_args()

        self.case_insensitive = self._handled_case_insensitive(kwargs)
        self.names = set(map(str.lower, names) if self.case_insensitive else names)

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (file_name := view_snapshot.file_name):
            raise AlwaysFalsyException("file not on disk")

        if self.case_insensitive:
            file_name = file_name.lower()
        return file_name in self.names
