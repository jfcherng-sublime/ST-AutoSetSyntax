from __future__ import annotations

from AutoSetSyntax.plugin import AbstractConstraint, ViewSnapshot


class MyOwnConstraint(AbstractConstraint):
    """Your custom `Constraint` must inherit `AbstractConstraint` and implement the `test` method."""

    def is_droppable(self) -> bool:
        # Optionally, you can implement `is_droppable` to indicate that this object
        # can be dropped under certain circumstances by the optimizer.
        return False

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        # Your job is to implement this function, at least.
        # This function tests the `view_snapshot`.
        return False
