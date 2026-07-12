from typing import Any
from typing import final
from typing import override

from ...constants import ST_PLATFORM_ARCH
from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsPlatformArchConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names = set(map(str.lower, self._handled_args()))
        self.result = ST_PLATFORM_ARCH in self.names

    @override
    def is_droppable(self) -> bool:
        # the platform/arch pair is fixed at install time, so a guaranteed non-match (self.result
        # is False) is just as much a constant as having no names at all
        return not self.names or not self.result

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.result
