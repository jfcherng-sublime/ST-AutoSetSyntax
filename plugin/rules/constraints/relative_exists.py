from pathlib import Path
from typing import Any, Tuple, final

import sublime

from ..constraint import AbstractConstraint, AlwaysFalsyException


@final
class RelativeExistsConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.relatives: Tuple[str, ...] = self._handled_args()
        self.match: str = kwargs.get("match", "any").lower()
        self.matcher = all if self.match == "all" else any

    def is_droppable(self) -> bool:
        return not self.relatives

    def test(self, view: sublime.View) -> bool:
        # file not on disk, maybe just a buffer
        if not (file_path := self.get_view_info(view)["file_path"]):
            raise AlwaysFalsyException("no filename")

        folder = Path(file_path).parent
        return self.matcher(
            (Path.is_dir if relative.endswith(("\\", "/")) else Path.is_file)(folder / relative)
            for relative in self.relatives
        )
