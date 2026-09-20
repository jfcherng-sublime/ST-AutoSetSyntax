from AutoSetSyntax.plugin import AbstractMatch
from AutoSetSyntax.plugin import MatchableRule
from AutoSetSyntax.plugin import ViewSnapshot


class MyOwnMatch(AbstractMatch):
    """Your custom `Match` must inherit `AbstractMatch` and implement the `test` method."""

    def fold(self, rules: tuple[MatchableRule, ...]) -> bool | None:
        # Optionally, you can implement `fold` to tell the optimizer that this combinator's
        # parameters and `rules` count already settle the answer, so it needn't be tested on
        # every view: return `True`/`False` for the constant `test` would always return, or
        # `None` when the result still depends on the view.
        return None

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        # Your job is to implement this function, at least.
        # This function tests `rules` (mix of `ConstraintRule`s and `MatchRule`s).
        return False
