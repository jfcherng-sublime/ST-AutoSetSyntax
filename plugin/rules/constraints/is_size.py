from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Comparator
from ...types import Fold
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


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
    def fold(self) -> Fold:
        if len(self.args) != 2:
            return Fold(False, f"expects exactly 2 args (a comparator and a threshold), got {len(self.args)}")
        if not self.comparator:
            return Fold(False, f"{self.args[0]!r} is not a known comparator")
        return UNFOLDED

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if (file_size := view_snapshot.file_size) < 0:
            raise AlwaysFalsyException("file not on disk")

        assert self.comparator
        return self.comparator(file_size, self.threshold)
