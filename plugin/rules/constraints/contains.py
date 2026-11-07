from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...types import Fold
from ...utils import str_finditer
from ..constraint import AbstractConstraint


@final
class ContainsConstraint(AbstractConstraint):
    args_noun = "needle to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()
        self.threshold = self._handled_threshold(kwargs)

    @override
    def fold(self) -> Fold:
        if self.threshold <= 0:
            return Fold(True, f'a "threshold" of {self.threshold} is met without finding anything')
        return super().fold()

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if self.threshold <= 0:
            return True

        return (
            nth(
                (_ for needle in self.needles for _ in str_finditer(view_snapshot.content, needle)),
                self.threshold - 1,
            )
            is not None
        )
