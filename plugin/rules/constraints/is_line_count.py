from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import Comparator
from ..constraint import AbstractConstraint


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

    @override
    def is_droppable(self) -> bool:
        return not (self.comparator and self.threshold is not None)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert self.comparator
        return self.comparator(view_snapshot.line_count, self.threshold)
