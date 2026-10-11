from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ...utils import str_finditer
from ..constraint import AbstractConstraint


@final
class ContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()
        self.threshold = self._handled_threshold(kwargs)

    @override
    def fold(self) -> Fold:
        """
        A threshold `<= 0` always matches. A positive threshold with no needles can never find a
        match.
        """
        if self.threshold <= 0:
            return Fold(True, f'a "threshold" of {self.threshold} is met without finding anything')
        return UNFOLDED if self.needles else Fold(False, "no needle to look for was given")

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
