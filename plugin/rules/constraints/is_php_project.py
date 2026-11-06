from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsPhpProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a PHP project."""

    marker = "composer.json"
