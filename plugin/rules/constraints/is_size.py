from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException


@final
class IsSizeConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.comparator, self.threshold = self._handled_comparison(self.args)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if (file_size := view_snapshot.file_size) < 0:
            raise AlwaysFalsyException("file not on disk")

        return self.comparator(file_size, self.threshold)
