from pathlib import Path
from typing import Set, final

import sublime

from ..constraint import AbstractConstraint


@final
class IsInPythonDjangoProjectConstraint(AbstractConstraint):
    """Check whether this file is in a (Python) Django project."""

    django_roots: Set[Path] = set()
    """Cached Django root directories."""

    def test(self, view: sublime.View) -> bool:
        view_info = self.get_view_info(view)

        if not view_info["file_path"]:
            return False

        file_path = Path(view_info["file_path"])

        # fast check from the cache
        if any((parent in self.django_roots) for parent in file_path.parents):
            return True

        # DJANGO_ROOT
        # ├── example_project
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
                    self.django_roots.add(parent)
                    return True

        return False
