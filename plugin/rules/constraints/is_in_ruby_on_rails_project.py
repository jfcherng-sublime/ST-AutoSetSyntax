from pathlib import Path
from typing import Set, final

import sublime

from ..constraint import AbstractConstraint


@final
class IsInRubyOnRailsProjectConstraint(AbstractConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    _project_roots: Set[Path] = set()
    """Cached project root directories."""

    def test(self, view: sublime.View) -> bool:
        cls = self.__class__
        view_info = self.get_view_info(view)

        if not view_info["file_path"]:
            return False

        file_path = Path(view_info["file_path"])

        # fast check from the cache
        if any((parent in cls._project_roots) for parent in file_path.parents):
            return True

        if project_root := self.find_parent_with_sibling(file_path, "config/routes.rb"):
            cls._project_roots.add(project_root)
            return True

        return False
