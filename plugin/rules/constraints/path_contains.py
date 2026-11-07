from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class PathContainsConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "needle to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # a file path, so follow the filesystem's case sensitivity like `is_name` does
        self.fix_case = self._handled_case_folder(kwargs)
        self.needles: tuple[str, ...] = self._handled_args(self.fix_case)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        file_path = view_snapshot.file_path

        file_path = self.fix_case(file_path)
        return any((needle in file_path) for needle in self.needles)
