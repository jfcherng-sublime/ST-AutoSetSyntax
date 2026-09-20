from AutoSetSyntax.plugin import UNFOLDED
from AutoSetSyntax.plugin import AbstractConstraint
from AutoSetSyntax.plugin import Fold
from AutoSetSyntax.plugin import ViewSnapshot


class MyOwnConstraint(AbstractConstraint):
    """Your custom `Constraint` must inherit `AbstractConstraint` and implement the `test` method."""

    def fold(self) -> Fold:
        # Optionally, you can implement `fold` to tell the optimizer that this object's
        # arguments already settle the answer, so it needn't be tested on every view:
        # return `Fold(True/False, "why")` for the constant `test` would always return, or
        # `UNFOLDED` when the result still depends on the view.
        # The reason is shown to the user in the dropped-rules report, so phrase it for them,
        # e.g. `Fold(False, "no extension was given")`.
        return UNFOLDED

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        # Your job is to implement this function, at least.
        # This function tests the `view_snapshot`.
        return False
