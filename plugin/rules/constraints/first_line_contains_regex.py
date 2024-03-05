from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class FirstLineContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return bool(self.regex.search(view_snapshot.first_line))
