from pathlib import Path
from typing import final, override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsInGitRepoConstraint(AbstractConstraint):
    """Check whether this file is in a git repo."""

    _successed_dirs: set[Path] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        # `.git/` directory for normal Git repo and `.git` file for Git worktree
        return self.find_parent_with_sibling_cached(view_snapshot, self._successed_dirs, ".git", use_exists=True)
