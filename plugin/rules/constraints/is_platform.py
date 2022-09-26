from typing import Any, final

import sublime

from ...constant import ST_PLATFORM
from ..constraint import AbstractConstraint


@final
class IsPlatformConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names = set(map(str.lower, self._handled_args()))
        self.result = ST_PLATFORM in self.names

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view: sublime.View) -> bool:
        return self.result
