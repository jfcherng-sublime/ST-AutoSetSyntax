from typing import Any, final, override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...utils import str_finditer
from ..constraint import AbstractConstraint


@final
class ContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()
        self.threshold: int = kwargs.get("threshold", 1)

    @override
    def is_droppable(self) -> bool:
        return not (self.needles and isinstance(self.threshold, (int, float)))

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
