from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ._text import AbstractRegexConstraint


@final
class NameContainsRegexConstraint(AbstractRegexConstraint):
    needs_file = True

    @override
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        return view_snapshot.file_name
