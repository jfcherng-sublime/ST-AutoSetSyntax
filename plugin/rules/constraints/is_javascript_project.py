from pathlib import Path
from typing import ClassVar
from typing import final
from typing import override

from more_itertools import first_true

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class IsJavascriptProjectConstraint(AbstractConstraint):
    """Check whether this file is in a JavaScript (non-TypeScript) project."""

    _successed_dirs: ClassVar[set[Path]] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (file_path_ := view_snapshot.file_path):
            raise AlwaysFalsyException("no filename")
        file_path = Path(file_path_)

        # fast check from the cache
        if first_true(file_path.parents, pred=lambda p: p in cls._successed_dirs):
            return True

        # "package.json" alone isn't enough: TypeScript projects have one too. The nearest
        # ancestor with "package.json" is the project root; it's only a JS (not TS) project if
        # that same root has no "tsconfig.json".
        for parent in file_path.parents:
            if not (parent / "package.json").is_file():
                continue
            if (parent / "tsconfig.json").is_file():
                return False
            cls._successed_dirs.add(parent)
            return True

        return False
