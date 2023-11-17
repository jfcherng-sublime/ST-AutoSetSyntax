from __future__ import annotations

from typing import Any, Callable, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException

Comparator = Callable[[Any, Any], bool]


@final
class IsSizeConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.comparator: Comparator | None = None
        self.threshold: float | None = None

        if len(self.args) != 2:
            return

        comparator, threshold = self.args

        self.comparator = self._handled_comparator(comparator)
        self.threshold = float(threshold)

    def is_droppable(self) -> bool:
        return not (self.comparator and self.threshold is not None)

    def test(self, view: sublime.View) -> bool:
        if (file_size := self.get_view_snapshot(view).file_size) < 0:
            raise AlwaysFalsyException("file not on disk")

        assert self.comparator
        return self.comparator(file_size, self.threshold)
