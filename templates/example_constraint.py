from AutoSetSyntax.plugin import AbstractConstraint
from typing import final
import sublime


@final
class MyOwnConstraint(AbstractConstraint):
    """Your custom `Constraint` must inherit `AbstractConstraint` and implement the `test` method."""

    def is_droppable(self) -> bool:
        # Optionally, you can implement `is_droppable` to indicate that this object
        # can be dropped under certain circumstances by the optimizer.
        return False

    def test(self, view: sublime.View) -> bool:
        # Your job is to implement this function, at least.
        # This function tests the `view`.
        # There is a @staticmethod which returns cached contexts for using.
        #     def get_view_info(view: sublime.View) -> TD_ViewSnapshot: ...
        return False
