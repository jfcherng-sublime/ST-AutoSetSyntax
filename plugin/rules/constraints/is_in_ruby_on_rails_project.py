from pathlib import Path
from typing import Set, final

import sublime

from ..constraint import AbstractConstraint


@final
class IsInRubyOnRailsProjectConstraint(AbstractConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    rails_roots: Set[Path] = set()
    """Cached Ruby on Rails root directories."""

    def test(self, view: sublime.View) -> bool:
        view_info = self.get_view_info(view)

        if not view_info["file_path"]:
            return False

        file_path = Path(view_info["file_path"])

        # fast check from the cache
        if any((parent in self.rails_roots) for parent in file_path.parents):
            return True

        if rails_root := self.find_parent_has_sibling(file_path, "config/routes.rb"):
            self.rails_roots.add(rails_root)
            return True

        return False
