from typing import Tuple, final

import sublime
from AutoSetSyntax.plugin import AbstractMatch, MatchableRule


@final
class MyOwnMatch(AbstractMatch):
    """Your custom `Match` must inherit `AbstractMatch` and implement the `test` method."""

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        # Optionally, you can implement `is_droppable` to indicate that this object
        # can be dropped under certain circumstances by the optimizer.
        return False

    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        # Your job is to implement this function, at least.
        # This function tests `rules` (mix of `ConstraintRule`s and `MatchRule`s).
        return False
