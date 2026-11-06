from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class IsHiddenSyntaxConstraint(AbstractConstraint):
    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (syntax := view_snapshot.syntax):
            raise AlwaysFalsyException(f"{view_snapshot.view} has no syntax")

        return syntax.hidden
