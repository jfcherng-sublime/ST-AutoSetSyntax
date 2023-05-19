from __future__ import annotations

from typing import Any, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsHiddenSyntaxConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def test(self, view: sublime.View) -> bool:
        if not (syntax := self.get_view_snapshot(view).syntax):
            raise AlwaysFalsyException(f"View({view.id()}) has no syntax")

        return syntax.hidden
