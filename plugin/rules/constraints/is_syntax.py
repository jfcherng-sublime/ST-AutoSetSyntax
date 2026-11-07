from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...utils import find_syntaxes
from ..constraint import AbstractConstraint


@final
class IsSyntaxConstraint(AbstractConstraint):
    args_noun = "syntax"
    needs_syntax = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.candidates: tuple[str, ...] = self._handled_args()

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert view_snapshot.syntax
        return view_snapshot.syntax in find_syntaxes(self.candidates)
