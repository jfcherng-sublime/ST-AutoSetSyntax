from __future__ import annotations

from pathlib import Path
from typing import final, override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsInRubyOnRailsProjectConstraint(AbstractConstraint):
    """Check whether this file is in a Ruby on Rails project."""

    _successed_dirs: set[Path] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.find_parent_with_sibling_cached(view_snapshot, self._successed_dirs, "config/routes.rb")
