from typing import Any, final

import sublime

from ...utils import nth
from ..constraint import AbstractConstraint


@final
class ContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)
        self.threshold: int = kwargs.get("threshold", 1)

    def is_droppable(self) -> bool:
        return not isinstance(self.threshold, (int, float))

    def test(self, view: sublime.View) -> bool:
        if self.threshold <= 0:
            return True

        return (
            nth(
                self.regex.finditer(self.get_view_snapshot(view).content),
                self.threshold - 1,
            )
            is not None
        )
