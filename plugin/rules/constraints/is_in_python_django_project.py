from pathlib import Path
from typing import final
from typing import override

from more_itertools import first_true

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class IsInPythonDjangoProjectConstraint(AbstractConstraint):
    """Check whether this file is in a (Python) Django project."""

    _successed_dirs: set[Path] = set()
    """Cached directories which make the result `True`."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (_file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("no filename")
        file_path = Path(_file_path)

        # fast check from the cache
        if first_true(file_path.parents, pred=lambda p: p in cls._successed_dirs):
            return True

        # [projectname]/         <- project root
        # ├── [projectname]/     <- Django root
        # │   ├── __init__.py
        # │   ├── settings.py
        # │   ├── urls.py
        # │   └── wsgi.py
        # └── manage.py

        for parent in file_path.parents:
            if not (parent / "manage.py").is_file():
                continue
            for sub_dir in filter(Path.is_dir, parent.glob("*")):
                if all((sub_dir / file).is_file() for file in ("settings.py", "urls.py", "wsgi.py")):
                    cls._successed_dirs.add(parent)
                    return True

        return False
