from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
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
