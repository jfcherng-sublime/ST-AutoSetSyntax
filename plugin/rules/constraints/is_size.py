from ..constraint import AbstractConstraint
from ..constraint import AlwaysFalsyException
from typing import Any, Callable, Optional, final
import sublime

Comparator = Callable[[Any, Any], bool]


@final
class IsSizeConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.comparator: Optional[Comparator] = None
        self.threshold: Optional[float] = None

        if len(self.args) != 2:
            return

        comparator, threshold = self.args

        self.comparator = self._handled_comparator(comparator)
        self.threshold = float(threshold)

    def is_droppable(self) -> bool:
        return not (self.comparator and self.threshold is not None)

    def test(self, view: sublime.View) -> bool:
        if (filesize := self.get_view_info(view)["file_size"]) < 0:
            raise AlwaysFalsyException("file not on disk")

        assert self.comparator
        return self.comparator(filesize, self.threshold)
