from pathlib import Path
from typing import final
from typing import override

from ._parent_marker import AbstractParentMarkerConstraint


@final
class IsInPythonDjangoProjectConstraint(AbstractParentMarkerConstraint):
    """Check whether this file is in a (Python) Django project."""

    # [projectname]/         <- project root
    # ├── [projectname]/     <- Django root
    # │   ├── __init__.py
    # │   ├── settings.py
    # │   ├── urls.py
    # │   └── wsgi.py
    # └── manage.py
    marker = "manage.py"

    @override
    def _holds_marker(self, directory: Path) -> bool:
        return super()._holds_marker(directory) and any(
            all((sub_dir / file).is_file() for file in ("settings.py", "urls.py", "wsgi.py"))
            for sub_dir in filter(Path.is_dir, directory.glob("*"))
        )
