from typing import final

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsInGitRepoConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a git repo."""

    # `.git/` directory for normal Git repo and `.git` file for Git worktree
    marker = ".git"
    use_exists = True
