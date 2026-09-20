from AutoSetSyntax.plugin import UNFOLDED
from AutoSetSyntax.plugin import AbstractMatch
from AutoSetSyntax.plugin import Fold
from AutoSetSyntax.plugin import MatchableRule
from AutoSetSyntax.plugin import ViewSnapshot


class MyOwnMatch(AbstractMatch):
    """Your custom `Match` must inherit `AbstractMatch` and implement the `test` method."""

    def fold(self, rules: tuple[MatchableRule, ...]) -> Fold:
        # Optionally, you can implement `fold` to tell the optimizer that this combinator's
        # parameters and `rules` count already settle the answer, so it needn't be tested on
        # every view: return `Fold(True/False, "why")` for the constant `test` would always
        # return, or `UNFOLDED` when the result still depends on the view.
        # The reason is shown to the user in the dropped-rules report, so phrase it for them,
        # e.g. `Fold(False, 'an "any" with no sub-rule matches nothing')`.
        return UNFOLDED

    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        # Your job is to implement this function, at least.
        # This function tests `rules` (mix of `ConstraintRule`s and `MatchRule`s).
        return False
