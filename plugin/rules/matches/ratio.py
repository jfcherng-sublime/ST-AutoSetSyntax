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

        self.numerator: float = nth(self.args, 0, 0)
        self.denominator: float = nth(self.args, 1, 0)
        self.ratio: float = (self.numerator / self.denominator) if self.denominator else -1

    @override
    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return not (self.denominator > 0 and 0 <= self.ratio <= 1)

    @override
    def droppable_value(self, rules: tuple[MatchableRule, ...]) -> bool:
        """
        With zero rules the goal `ceil(ratio * 0)` is always `0` (constant True) no matter the
        ratio. Otherwise, an invalid/negative ratio (bad denominator, or a negative numerator)
        also means `goal <= 0` (constant True); a ratio above `1` means the goal exceeds
        `len(rules)`, which can never be satisfied (constant False).
        """
        return not rules or self.ratio < 0

    @override
    def prunable_child_value(self) -> bool | None:
        """
        `None`: no child is ever safely prunable here. Unlike `all`/`any`/`some`, this match's
        goal (`ceil(ratio * len(rules))`) is recomputed from the *current* rule count on every
        `test()`, so removing any child -- constant or not -- shifts the effective threshold
        rather than leaving the result unchanged. Pruning is left entirely to
        `SyntaxRule.optimize()`/`MatchRule.optimize()` collapsing this whole match instead, via
        `is_droppable()`/`droppable_value()`, once/if the match itself becomes provably constant.
        """
        return None

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, math.ceil(self.ratio * len(rules)))
