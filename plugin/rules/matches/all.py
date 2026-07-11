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
        """`all([])` is `True`, so an empty `all` is a constant True -- unlike an empty `any`, which is False."""
        return True

    @override
    def prunable_child_value(self) -> bool | None:
        """
        Only a constant-True child is safe to drop: `True` is AND's identity element, so
        `all(True, x) == all(x)`. A constant-False child must stay (or force this whole `all`
        to `False`), since `all(False, x)` is always `False` regardless of `x`.
        """
        return True

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return all(rule.test(view_snapshot) for rule in rules)
