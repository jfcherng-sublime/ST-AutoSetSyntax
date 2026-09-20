from AutoSetSyntax.plugin import AbstractConstraint
from AutoSetSyntax.plugin import ViewSnapshot


class MyOwnConstraint(AbstractConstraint):
    """Your custom `Constraint` must inherit `AbstractConstraint` and implement the `test` method."""

    def fold(self) -> bool | None:
        # Optionally, you can implement `fold` to tell the optimizer that this object's
        # arguments already settle the answer, so it needn't be tested on every view:
        # return `True`/`False` for the constant `test` would always return, or
        # `None` when the result still depends on the view.
        return None

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        # Your job is to implement this function, at least.
        # This function tests the `view_snapshot`.
        return False
