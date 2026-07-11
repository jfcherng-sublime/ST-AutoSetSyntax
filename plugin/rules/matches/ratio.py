import math
from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class RatioMatch(AbstractMatch):
    """Matches ratio like `(2, 3)`, which means at least two thirds of rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.numerator: float = nth(self.args, 0) or 0
        self.denominator: float = nth(self.args, 1) or 0
        self.ratio: float = (self.numerator / self.denominator) if self.denominator else -1

    @override
    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return not (self.denominator > 0 and 0 <= self.ratio <= 1)

    @override
    def droppable_value(self, rules: tuple[MatchableRule, ...]) -> bool:
        """With no rules the goal is always 0 (always satisfied); an invalid/negative ratio is too."""
        return not rules or self.ratio < 0

    @override
    def prunable_child_value(self) -> bool | None:
        """
        The goal is `ceil(ratio * len(rules))`, recomputed from the *current* rule count, so removing
        any child -- even a constant one -- would shift the effective threshold. Never safe to prune.
        """
        return None

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, math.ceil(self.ratio * len(rules)))
