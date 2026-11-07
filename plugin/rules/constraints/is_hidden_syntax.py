from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsHiddenSyntaxConstraint(AbstractConstraint):
    needs_syntax = True

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        assert view_snapshot.syntax
        return view_snapshot.syntax.hidden
