from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..constraint import AbstractConstraint


@final
class ContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)
        self.threshold = self._handled_threshold(kwargs)

    @override
    def fold(self) -> Fold:
        """
        A threshold `<= 0` always matches. A positive threshold with no patterns can never find a
        match (the "match nothing" regex from `merge_regexes(())` guarantees that).
        """
        if self.threshold <= 0:
            return Fold(True, f'a "threshold" of {self.threshold} is met without finding anything')
        return UNFOLDED if any(self.args) else Fold(False, "no pattern to look for was given")

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if self.threshold <= 0:
            return True

        return (
            nth(
                self.regex.finditer(view_snapshot.content),
                self.threshold - 1,
            )
            is not None
        )
