from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ._text import AbstractNeedlesConstraint


@final
class PathContainsConstraint(AbstractNeedlesConstraint):
    needs_file = True
    folds_case = True

    @override
    def subject(self, view_snapshot: ViewSnapshot) -> str:
        return view_snapshot.file_path
