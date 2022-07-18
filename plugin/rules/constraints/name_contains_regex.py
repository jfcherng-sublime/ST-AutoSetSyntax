from typing import Any, final

import sublime

from ..constraint import AbstractConstraint


@final
class NameContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    def test(self, view: sublime.View) -> bool:
        return bool(self.regex.search(self.get_view_info(view)["file_name"]))
