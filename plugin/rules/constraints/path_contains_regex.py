from ..constraint import AbstractConstraint
from typing import Any
import sublime


class PathContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._setup_regex()

    def test(self, view: sublime.View) -> bool:
        return bool(self.regex.search(self.get_view_info(view)["file_path"]))
