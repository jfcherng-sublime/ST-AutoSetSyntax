from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class AllMatch(AbstractMatch):
    """Matches when all rules are matched."""

    @override
    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    @override
    def droppable_value(self, rules: tuple[MatchableRule, ...]) -> bool:
        """`all([])` is `True`, so an empty `all` is a constant True, not False."""
        return True

    @override
    def prunable_child_value(self) -> bool | None:
        """Only a constant-True child is safe to drop (`True` is AND's identity element)."""
        return True

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return all(rule.test(view_snapshot) for rule in rules)
