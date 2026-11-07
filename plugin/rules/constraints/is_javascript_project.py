from pathlib import Path
from typing import ClassVar
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsJavascriptProjectConstraint(AbstractConstraint):
    """Check whether this file is in a JavaScript (non-TypeScript) project."""

    needs_file = True

    _found_dirs: ClassVar[set[Path]] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        cls = self.__class__

        file_path = Path(view_snapshot.file_path)

        # "package.json" alone isn't enough: TypeScript projects have one too. The nearest
        # ancestor with "package.json" is the project root; it's only a JS (not TS) project if
        # that same root has no "tsconfig.json".
        for parent in file_path.parents:
            # the cache only answers once no nearer root has been found on the way up -- a cached
            # JS root can hold a nested TS package, whose files it must not claim
            if parent in cls._found_dirs:
                return True
            if not (parent / "package.json").is_file():
                continue
            if (parent / "tsconfig.json").is_file():
                return False
            cls._found_dirs.add(parent)
            return True

        return False
