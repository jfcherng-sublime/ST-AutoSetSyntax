from __future__ import annotations

from typing import Any, Callable, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint

Comparator = Callable[[Any, Any], bool]


@final
class IsLineCountConstraint(AbstractConstraint):
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

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.comparator
        return self.comparator(view_snapshot.line_count, self.threshold)
