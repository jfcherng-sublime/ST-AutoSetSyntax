from typing import Any, final, override

from ...snapshot import ViewSnapshot
from ...types import Comparator
from ..constraint import AbstractConstraint, AlwaysFalsyException


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

    @override
    def is_droppable(self) -> bool:
        return not (self.comparator and self.threshold is not None)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if (file_size := view_snapshot.file_size) < 0:
            raise AlwaysFalsyException("file not on disk")

        assert self.comparator
        return self.comparator(file_size, self.threshold)
