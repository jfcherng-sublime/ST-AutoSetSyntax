from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class PathContainsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # a file path, so follow the filesystem's case sensitivity like `is_name` does
        self.case_insensitive = self._handled_case_insensitive(kwargs)
        self.needles: tuple[str, ...] = self._handled_args(self.fix_case)

    @override
    def fold(self) -> Fold:
        return UNFOLDED if self.needles else Fold(False, "no needle to look for was given")

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("file not on disk")

        file_path = self.fix_case(file_path)
        return any((needle in file_path) for needle in self.needles)

    def fix_case(self, string: str) -> str:
        return string.lower() if self.case_insensitive else string
