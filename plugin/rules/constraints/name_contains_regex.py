from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class NameContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def fold(self) -> bool | None:
        """With no patterns, `merge_regexes(())` compiles a "match nothing" regex, so `test()`
        always fails."""
        return None if any(self.args) else False

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not (file_name := view_snapshot.file_name):
            raise AlwaysFalsyException("file not on disk")

        return bool(self.regex.search(file_name))
