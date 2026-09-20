from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..constraint import AbstractConstraint


@final
class FirstLineContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()

    @override
    def fold(self) -> Fold:
        return UNFOLDED if self.needles else Fold(False, "no needle to look for was given")

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return any((needle in view_snapshot.first_line) for needle in self.needles)
