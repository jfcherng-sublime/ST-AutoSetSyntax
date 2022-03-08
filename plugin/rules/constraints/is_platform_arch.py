from ...constant import ST_PLATFORM_ARCH
from ..constraint import AbstractConstraint
from typing import Any, Tuple, final
import sublime


@final
class IsPlatformArchConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names: Tuple[str, ...] = self._handled_args()
        self.names = tuple(map(str.lower, self.names))

        # this can be checked in compile time directly
        self.result = ST_PLATFORM_ARCH in self.names

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view: sublime.View) -> bool:
        return self.result
