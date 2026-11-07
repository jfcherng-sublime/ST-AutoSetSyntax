from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...types import Fold
from ..constraint import AbstractConstraint


@final
class ContainsRegexConstraint(AbstractConstraint):
    args_noun = "pattern to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)
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
                self.regex.finditer(view_snapshot.content),
                self.threshold - 1,
            )
            is not None
        )
