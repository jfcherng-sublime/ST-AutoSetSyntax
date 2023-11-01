from __future__ import annotations

from pathlib import Path
from typing import final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class IsInPythonDjangoProjectConstraint(AbstractConstraint):
    """Check whether this file is in a (Python) Django project."""

    _success_dirs: set[Path] = set()
    """Cached directories which make the result `True`."""

    def test(self, view: sublime.View) -> bool:
        cls = self.__class__

        # file not on disk, maybe just a buffer
        if not (_file_path := self.get_view_snapshot(view).file_path):
            raise AlwaysFalsyException("no filename")
        file_path = Path(_file_path)

        # fast check from the cache
        if any(map(lambda p: p in cls._success_dirs, file_path.parents)):
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
                    cls._success_dirs.add(parent)
                    return True

        return False
