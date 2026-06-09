from pathlib import Path
from typing import ClassVar
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsInHgRepoConstraint(AbstractConstraint):
    """Check whether this file is in a Mercurial repo."""

    _successed_dirs: ClassVar[set[Path]] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.find_parent_with_sibling_cached(view_snapshot, self._successed_dirs, ".hg/")
