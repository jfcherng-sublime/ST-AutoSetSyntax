from collections.abc import Iterable
from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ._text import AbstractOccurrencesConstraint


@final
class ContainsRegexConstraint(AbstractOccurrencesConstraint):
    args_noun = "pattern to look for"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        return view_snapshot.content

    @override
    def occurrences(self, text: str) -> Iterable[object]:
        return self.regex.finditer(text)
