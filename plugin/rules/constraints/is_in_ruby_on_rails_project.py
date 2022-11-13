from pathlib import Path
from typing import Set, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsInRubyOnRailsProjectConstraint(AbstractConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    _success_dirs: Set[Path] = set()
    """Cached directories which make the result `True`."""

    def test(self, view: sublime.View) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (_file_path := self.get_view_snapshot(view).file_path):
            raise AlwaysFalsyException("no filename")
        file_path = Path(_file_path)

        # fast check from the cache
        if any((parent in cls._success_dirs) for parent in file_path.parents):
            return True

        if project_root := self.find_parent_with_sibling(file_path, "config/routes.rb"):
            cls._success_dirs.add(project_root)
            return True

        return False
