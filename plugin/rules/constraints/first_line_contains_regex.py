from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class FirstLineContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def is_droppable(self) -> bool:
        """With no patterns, `merge_regexes(())` compiles a "match nothing" regex, so `test()`
        always fails."""
        return not any(self.args)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return bool(self.regex.search(view_snapshot.first_line))
