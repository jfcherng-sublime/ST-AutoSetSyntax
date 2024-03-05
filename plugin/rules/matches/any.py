from __future__ import annotations

from typing import final

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch, MatchableRule


@final
class AnyMatch(AbstractMatch):
    """Matches when any rule is matched."""

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return any(rule.test(view_snapshot) for rule in rules)
