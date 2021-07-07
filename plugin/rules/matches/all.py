from ..match import AbstractMatch
from ..match import MatchableRule
from typing import Tuple
import sublime


class AllMatch(AbstractMatch):
    """Matches when all rules are matched."""

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        return all(rule.test(view) for rule in rules)
