from collections.abc import Iterable
from typing import Any
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...utils import str_finditer
from ._text import AbstractOccurrencesConstraint


@final
class ContainsConstraint(AbstractOccurrencesConstraint):
    args_noun = "needle to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.needles: tuple[str, ...] = self._handled_args()

    @override
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        return view_snapshot.content

    @override
    def occurrences(self, text: str) -> Iterable[int]:
        return (idx for needle in self.needles for idx in str_finditer(text, needle))
