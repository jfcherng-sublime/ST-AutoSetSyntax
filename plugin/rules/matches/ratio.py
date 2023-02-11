from typing import Any, Tuple, final

import sublime

from ...utils import nth
from ..match import AbstractMatch, MatchableRule


@final
class RatioMatch(AbstractMatch):
    """Matches ratio like `(2, 3)`, which means at least two thirds of rules should be matched."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.numerator: float = nth(self.args, 0) or 0
        self.denominator: float = nth(self.args, 1) or 0
        self.ratio: float = (self.numerator / self.denominator) if self.denominator else -1

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        return not (self.denominator > 0 and 0 <= self.ratio <= 1)

    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        return self.test_count(view, rules, self.ratio * len(rules))
