from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class NameContainsRegexConstraint(AbstractConstraint):
    needs_file = True
    args_noun = "pattern to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        file_name = view_snapshot.file_name

        return bool(self.regex.search(file_name))
