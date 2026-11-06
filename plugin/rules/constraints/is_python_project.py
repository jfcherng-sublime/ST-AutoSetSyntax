from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsPythonProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a Python project."""

    marker = "pyproject.toml"
