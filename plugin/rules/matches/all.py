from __future__ import annotations

from typing import final

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch, MatchableRule


@final
class AllMatch(AbstractMatch):
    """Matches when all rules are matched."""

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return all(rule.test(view_snapshot) for rule in rules)
