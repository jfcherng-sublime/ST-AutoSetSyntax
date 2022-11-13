from pathlib import Path
from typing import Set, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsInGitRepoConstraint(AbstractConstraint):
    """Check whether this file is in a git repo."""

    _success_dirs: Set[Path] = set()
    """Cached directories which make the result `True`."""

    def test(self, view: sublime.View) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (_file_path := self.get_view_snapshot(view).file_path):
            raise AlwaysFalsyException("file not on disk")
        file_path = Path(_file_path)

        # fast check from the cache
        if any((parent in cls._success_dirs) for parent in file_path.parents):
            return True

        # `.git/` directory for normal Git repo and `.git` file for Git worktree
        if _major_dir := self.find_parent_with_sibling(file_path, ".git", use_exists=True):
            cls._success_dirs.add(_major_dir)
            return True

        return False
