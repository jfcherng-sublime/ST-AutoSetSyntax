from typing import Any
from typing import final
from typing import override

from ...constants import ST_PLATFORM_ARCH
from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ...utils import quote_join
from ..constraint import AbstractConstraint


@final
class IsPlatformArchConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names = set(map(str.lower, self._handled_args()))
        self.result = ST_PLATFORM_ARCH in self.names

    @override
    def fold(self) -> Fold:
        # the platform/arch pair is fixed at install time, so a guaranteed non-match (self.result
        # is False) is just as much a constant as having no names at all
        if not self.names:
            return Fold(False, "no platform/arch pair was given")
        if not self.result:
            return Fold(False, f"this Sublime Text is {ST_PLATFORM_ARCH}, not any of {quote_join(sorted(self.names))}")
        return UNFOLDED

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.result
