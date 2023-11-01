from __future__ import annotations

from typing import final

import sublime

from ..match import AbstractMatch, MatchableRule


@final
class AllMatch(AbstractMatch):
    """Matches when all rules are matched."""

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    def test(self, view: sublime.View, rules: tuple[MatchableRule, ...]) -> bool:
        return all(rule.test(view) for rule in rules)
