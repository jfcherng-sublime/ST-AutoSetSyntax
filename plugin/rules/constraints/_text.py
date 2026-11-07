from abc import abstractmethod
from collections.abc import Iterable
from typing import Any
from typing import ClassVar
from typing import override

from more_itertools import nth

from ...snapshot import ViewSnapshot
from ...types import Fold
from ..constraint import AbstractConstraint


class AbstractTextConstraint(AbstractConstraint):
    """A constraint about one piece of text of the view; a subclass only names which (`subject()`)."""

    @abstractmethod
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        """The text to look into."""


class AbstractNeedlesConstraint(AbstractTextConstraint):
    """Passes when the subject contains any of the given literal needles."""

    args_noun = "needle to look for"

    folds_case: ClassVar[bool] = False
    """Whether case follows the filesystem's (`case_insensitive` in kwargs, defaulted to the platform's)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fix_case = self._handled_case_folder(kwargs) if self.folds_case else str
        self.needles: tuple[str, ...] = self._handled_args(self.fix_case)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        subject = self.fix_case(self.subject(view_snapshot))
        return any(needle in subject for needle in self.needles)


class AbstractRegexConstraint(AbstractTextConstraint):
    """Passes when the subject has a match of the given regexes."""

    args_noun = "pattern to look for"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.regex = self._handled_regex(self.args, self.kwargs)

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return bool(self.regex.search(self.subject(view_snapshot)))


class AbstractOccurrencesConstraint(AbstractTextConstraint):
    """Passes when the subject has at least `threshold` (kwargs, defaulted to `1`) occurrences."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.threshold = self._handled_threshold(kwargs)

    @abstractmethod
    def occurrences(self, text: str) -> Iterable[object]:
        """Each place something was found in `text`."""

    @override
    def fold(self) -> Fold:
        if self.threshold <= 0:
            return Fold(True, f'a "threshold" of {self.threshold} is met without finding anything')
        return super().fold()

    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if self.threshold <= 0:
            return True
        return nth(self.occurrences(self.subject(view_snapshot)), self.threshold - 1) is not None
