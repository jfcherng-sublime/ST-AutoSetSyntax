from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class PathContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (file_path := view_snapshot.file_path):
            raise AlwaysFalsyException("file not on disk")

        return bool(self.regex.search(file_path))
