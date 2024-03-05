from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsHiddenSyntaxConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (syntax := view_snapshot.syntax):
            raise AlwaysFalsyException(f"{view_snapshot.view} has no syntax")

        return syntax.hidden
