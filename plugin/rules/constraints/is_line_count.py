from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsLineCountConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.comparator, self.threshold = self._handled_comparison(self.args)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return self.comparator(view_snapshot.line_count, self.threshold)
