from pathlib import Path
from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class RelativeExistsConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "relative path"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.relatives: tuple[str, ...] = self._handled_args()
        self.match: str = (kwargs.get("match") or "any").lower()
        self.matcher = all if self.match == "all" else any

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        file_path = view_snapshot.file_path

        folder = Path(file_path).parent
        return self.matcher(
            (Path.is_dir if relative.endswith(("\\", "/")) else Path.is_file)(folder / relative)
            for relative in self.relatives
        )
