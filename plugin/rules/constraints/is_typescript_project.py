from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsTypescriptProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a TypeScript project."""

    marker = "tsconfig.json"
