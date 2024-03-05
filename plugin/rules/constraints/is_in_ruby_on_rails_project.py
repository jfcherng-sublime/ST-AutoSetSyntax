from __future__ import annotations

from pathlib import Path
from typing import final

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsInRubyOnRailsProjectConstraint(AbstractConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    _success_dirs: set[Path] = set()
    """Cached directories which make the result `True`."""

    def test(self, view_snapshot: ViewSnapshot) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (_file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("no filename")
        file_path = Path(_file_path)

        # fast check from the cache
        if any(map(lambda p: p in cls._success_dirs, file_path.parents)):
            return True

        if project_root := self.find_parent_with_sibling(file_path, "config/routes.rb"):
            cls._success_dirs.add(project_root)
            return True

        return False
