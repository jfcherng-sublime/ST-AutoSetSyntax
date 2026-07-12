from typing import Any
from typing import final
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class ContainsRegexConstraint(AbstractConstraint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)
        self.threshold: int = kwargs.get("threshold", 1)

    @override
    def is_droppable(self) -> bool:
        """
        A non-numeric threshold makes `test()` always raise (caught upstream as `False`). A
        positive threshold with no patterns can never find a match (the "match nothing" regex
        from `merge_regexes(())` guarantees that). A threshold `<= 0` is a constant `True`,
        though -- not droppable, since droppable must mean `test()` always fails (`False`), and
        there's no way to represent a constant-`True` constraint here.
        """
        if not isinstance(self.threshold, (int, float)):
            return True
        return self.threshold > 0 and not self.args

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if self.threshold <= 0:
            return True

        return (
            nth(
                self.regex.finditer(view_snapshot.content),
                self.threshold - 1,
            )
            is not None
        )
