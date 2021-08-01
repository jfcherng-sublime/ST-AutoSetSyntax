from ..constraint import AbstractConstraint
from typing import Any
import sublime


class ContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)
        self.threshold: int = kwargs.get("threshold", 1)

    def is_droppable(self) -> bool:
        return not isinstance(self.threshold, (int, float))

    def test(self, view: sublime.View) -> bool:
        content = self.get_view_info(view)["content"]
        count = 0
        for _ in self.regex.finditer(content):
            count += 1
            if count >= self.threshold:
                return True
        return False
