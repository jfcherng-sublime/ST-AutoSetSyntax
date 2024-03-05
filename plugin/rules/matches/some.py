from __future__ import annotations

from typing import Any, final

from ...snapshot import ViewSnapshot
from ...utils import nth
from ..match import AbstractMatch, MatchableRule


@final
class SomeMatch(AbstractMatch):
    """Matches some like `(5,)`, which means at least 5 rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.count: float = nth(self.args, 0) or -1

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return not (0 <= self.count <= len(rules))

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, self.count)
