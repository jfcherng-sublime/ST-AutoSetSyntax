from typing import Any, final, override

from ...snapshot import ViewSnapshot
from ...utils import find_syntaxes_by_syntax_likes
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsSyntaxConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.candidates: tuple[str, ...] = self._handled_args()

    @override
    def is_droppable(self) -> bool:
        return not self.candidates

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (syntax := view_snapshot.syntax):
            raise AlwaysFalsyException(f"{view_snapshot.view} has no syntax")

        return syntax in find_syntaxes_by_syntax_likes(self.candidates)
