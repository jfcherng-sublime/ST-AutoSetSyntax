from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsInSvnRepoConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a SVN repo."""

    marker = ".svn/"
