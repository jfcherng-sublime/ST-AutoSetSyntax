from typing import Any
from typing import final
from typing import override

from ...constants import ST_PLATFORM
from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsPlatformConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names = set(map(str.lower, self._handled_args()))
        self.result = ST_PLATFORM in self.names

    @override
    def fold(self) -> bool | None:
        # the platform is fixed at install time, so a guaranteed non-match (self.result is
        # False) is just as much a constant as having no names at all
        return None if (self.names and self.result) else False

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.result
