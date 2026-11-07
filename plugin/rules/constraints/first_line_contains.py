from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ._text import AbstractNeedlesConstraint


@final
class FirstLineContainsConstraint(AbstractNeedlesConstraint):
    @override
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        return view_snapshot.first_line
