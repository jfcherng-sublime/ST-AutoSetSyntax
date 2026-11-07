from abc import abstractmethod
from pathlib import Path
from typing import ClassVar
from typing import override

from more_itertools import first_true

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


class AbstractParentMarkerConstraint(AbstractConstraint):
    """
    Passes for a file under a directory that holds a marker: `.git`, `go.mod`, `Cargo.toml`...

    A subclass only names its `marker`. A marker ending in `/` must be a directory; otherwise it is a
    file, or either when `use_exists` is set.
    """

    needs_file = True

    use_exists: ClassVar[bool] = False

    _found_dirs: ClassVar[set[Path]]
    """The directories known to hold the marker. It is per subclass, since each has its own marker."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls._found_dirs = set()

    @property
    @abstractmethod
    def marker(self) -> str:
        """The name, relative to a parent directory, that makes the file pass."""

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        parents = Path(view_snapshot.file_path).parents

        if first_true(parents, pred=lambda parent: parent in self._found_dirs):
            return True

        if found := first_true(parents, pred=self._holds_marker):
            self._found_dirs.add(found)
            return True

        return False

    def _holds_marker(self, directory: Path) -> bool:
        if self.use_exists:
            return (directory / self.marker).exists()
        if self.marker.endswith(("\\", "/")):
            return (directory / self.marker).is_dir()
        return (directory / self.marker).is_file()
