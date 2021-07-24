from ..constraint import AbstractConstraint
from typing import Any, Tuple
import sublime


class IsNameConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.names: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.names

    def test(self, view: sublime.View) -> bool:
        return self.get_view_info(view)["file_name"] in self.names
