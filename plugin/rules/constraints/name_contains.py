from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class NameContainsConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "needle to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # a file name, so follow the filesystem's case sensitivity like `is_name` does
        self.fix_case = self._handled_case_folder(kwargs)
        self.needles: tuple[str, ...] = self._handled_args(self.fix_case)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        file_name = view_snapshot.file_name

        file_name = self.fix_case(file_name)
        return any((needle in file_name) for needle in self.needles)
