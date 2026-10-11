import math
from fractions import Fraction
from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class RatioMatch(AbstractMatch):
    """Matches ratio like `(2, 3)`, which means at least two thirds of rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # reject rather than default: an invalid ratio used to mean "demands nothing", i.e. a typo
        # made the rule match every file. Raising makes the whole rule invalid instead
        if not (
            len(self.args) == 2 and all(map(_is_finite_number, self.args)) and self.args[0] >= 0 and self.args[1] > 0
        ):
            raise ValueError(
                '"ratio" needs exactly two numbers, a non-negative numerator and a positive denominator,'
                f" got {list(self.args)}"
            )
        self.numerator: float = self.args[0]
        self.denominator: float = self.args[1]
        # exact arithmetic: in floats `0.28 * 25` is `7.000000000000001`, which `ceil()` turns into
        # a goal of 8. `limit_denominator()` recovers the fraction a float like `0.28` was written as
        self.ratio = Fraction(self.numerator).limit_denominator() / Fraction(self.denominator).limit_denominator()

    @override
    def fold(self, rules: tuple[MatchableRule, ...]) -> Fold:
        """
        With zero rules, or a ratio of `0`, the goal `ceil(ratio * len(rules))` is `0`: constant
        True. A ratio above `1` means the goal exceeds `len(rules)`, which can never be
        satisfied: constant False.
        """
        # every reason is built inside the branch that returns it, so the common case -- a
        # ratio that still depends on the view -- formats nothing
        if not rules:
            return Fold(True, 'a "ratio" with no sub-rule has nothing left to satisfy')
        if self.ratio == 0:
            return Fold(True, f"a ratio of {self.numerator}/{self.denominator} is met without any sub-rule passing")
        if self.ratio > 1:
            return Fold(
                False,
                f"a ratio of {self.numerator}/{self.denominator} needs more than all {len(rules)} sub-rule(s) to pass",
            )
        return UNFOLDED

    @override
    def prunable_child_value(self) -> bool | None:
        """
        `None`: no child is ever safely prunable here. Unlike `all`/`any`/`some`, this match's
        goal (`ceil(ratio * len(rules))`) is recomputed from the *current* rule count on every
        `test()`, so removing any child -- constant or not -- shifts the effective threshold
        rather than leaving the result unchanged. Pruning is left entirely to
        `SyntaxRule.optimize()`/`MatchRule.optimize()` collapsing this whole match instead, via
        `fold()`, once/if the match itself becomes provably constant.
        """
        return None

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view_snapshot, rules, math.ceil(self.ratio * len(rules)))


def _is_finite_number(value: Any) -> bool:
    # `bool` is an `int` subclass, but `true` in settings is surely not meant as the number 1
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
