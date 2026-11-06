from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsInHgRepoConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a Mercurial repo."""

    marker = ".hg/"
