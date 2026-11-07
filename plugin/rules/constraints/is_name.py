from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsNameConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "file name"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fix_case = self._handled_case_folder(kwargs)
        self.names = set(self._handled_args(self.fix_case))

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.fix_case(view_snapshot.file_name) in self.names
