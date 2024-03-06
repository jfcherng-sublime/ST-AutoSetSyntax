from __future__ import annotations

from AutoSetSyntax.plugin import AbstractMatch, MatchableRule, ViewSnapshot


class MyOwnMatch(AbstractMatch):
    """Your custom `Match` must inherit `AbstractMatch` and implement the `test` method."""

    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        # Optionally, you can implement `is_droppable` to indicate that this object
        # can be dropped under certain circumstances by the optimizer.
        return False

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        # Your job is to implement this function, at least.
        # This function tests `rules` (mix of `ConstraintRule`s and `MatchRule`s).
        return False
