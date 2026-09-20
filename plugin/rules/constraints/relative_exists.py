from pathlib import Path
from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class RelativeExistsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.relatives: tuple[str, ...] = self._handled_args()
        # "match": null is present with value None, not absent, so .get(..., "any")'s default
        # doesn't cover it -- None.lower() would raise AttributeError
        self.match: str = (kwargs.get("match") or "any").lower()
        self.matcher = all if self.match == "all" else any

    @override
    def fold(self) -> Fold:
        return UNFOLDED if self.relatives else Fold(False, "no relative path was given")

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        # file not on disk, maybe just a buffer
        if not (file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("no filename")

        folder = Path(file_path).parent
        return self.matcher(
            (Path.is_dir if relative.endswith(("\\", "/")) else Path.is_file)(folder / relative)
            for relative in self.relatives
        )
