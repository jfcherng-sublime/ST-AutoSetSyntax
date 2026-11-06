from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsGoProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a Go project."""

    marker = "go.mod"
