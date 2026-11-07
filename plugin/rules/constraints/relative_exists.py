from pathlib import Path
from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...utils import holds_entry
from ..constraint import AbstractConstraint


@final
class RelativeExistsConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "relative path"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.relatives: tuple[str, ...] = self._handled_args()
        self.match: str = (kwargs.get("match") or "any").lower()
        if self.match not in {"any", "all"}:
            raise ValueError(f'"match" must be "any" or "all", got {self.match!r}')
        self.matcher = all if self.match == "all" else any

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        file_path = view_snapshot.file_path

        folder = Path(file_path).parent
        return self.matcher(holds_entry(folder, relative) for relative in self.relatives)
