from ..match import AbstractMatch
from ..match import MatchableRule
from typing import Tuple, final
import sublime


@final
class AnyMatch(AbstractMatch):
    """Matches when any rule is matched."""

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        return any(rule.test(view) for rule in rules)
