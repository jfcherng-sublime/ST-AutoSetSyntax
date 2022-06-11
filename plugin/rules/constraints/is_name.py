from ..constraint import AbstractConstraint
from typing import Any, Tuple, final
import sublime


@final
class IsNameConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        names: Tuple[str, ...] = self._handled_args()

        self.case_insensitive = self._handled_case_insensitive(args, kwargs)
        self.names = set(map(str.lower, names) if self.case_insensitive else names)

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view: sublime.View) -> bool:
        filename = self.get_view_info(view)["file_name"]
        if self.case_insensitive:
            filename = filename.lower()
        return filename in self.names
