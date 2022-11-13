from typing import Any, Tuple, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class NameContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.needles

    def test(self, view: sublime.View) -> bool:
        if not (file_name := self.get_view_snapshot(view).file_name):
            raise AlwaysFalsyException("file not on disk")

        return any((needle in file_name) for needle in self.needles)
