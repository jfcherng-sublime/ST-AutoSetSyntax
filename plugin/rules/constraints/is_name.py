from ..constraint import AbstractConstraint
from typing import Any, Tuple
import sublime


class IsNameConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names: Tuple[str, ...] = self._handled_args()
        self.case_insensitive: bool = bool(kwargs.get("case_insensitive", sublime.platform() == "windows"))

        if self.case_insensitive:
            self.names = tuple(name.lower() for name in self.names)

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view: sublime.View) -> bool:
        filename = self.get_view_info(view)["file_name"]
        if self.case_insensitive:
            filename = filename.lower()
        return filename in self.names
