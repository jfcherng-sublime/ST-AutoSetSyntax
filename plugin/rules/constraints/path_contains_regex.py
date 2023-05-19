from __future__ import annotations

from typing import Any, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class PathContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    def test(self, view: sublime.View) -> bool:
        if not (file_path := self.get_view_snapshot(view).file_path):
            raise AlwaysFalsyException("file not on disk")

        return bool(self.regex.search(file_path))
