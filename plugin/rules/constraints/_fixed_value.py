from abc import abstractmethod
from typing import Any
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ...utils import quote_join
from ..constraint import AbstractConstraint


class AbstractFixedValueConstraint(AbstractConstraint):
    """
    Passes when a value fixed at install time (the platform, the architecture...) is one of the
    given names. The answer never depends on the view, so it is decided once, on creation.
    """

    @property
    @abstractmethod
    def current(self) -> str:
        """This Sublime Text's value, in lower case."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names = set(map(str.lower, self._handled_args()))
        self.result = self.current in self.names

    @override
    def fold(self) -> Fold:
        if (fold := super().fold()) is not UNFOLDED:
            return fold
        if not self.result:
            return Fold(False, f"this Sublime Text is {self.current}, not any of {quote_join(sorted(self.names))}")
        return UNFOLDED

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.result
