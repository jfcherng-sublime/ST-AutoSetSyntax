from typing import Any, Tuple, final

import sublime

from ...helper import find_syntaxes_by_syntax_like
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsSyntaxConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.candidates: Tuple[str, ...] = self._handled_args()

    def is_droppable(self) -> bool:
        return not self.candidates

    def test(self, view: sublime.View) -> bool:
        if not (syntax := self.get_view_snapshot(view).syntax):
            raise AlwaysFalsyException(f"View({view.id()}) has no syntax")

        return any((syntax in find_syntaxes_by_syntax_like(candidate)) for candidate in self.candidates)
