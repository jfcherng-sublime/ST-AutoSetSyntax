from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsMagikaEnabledConstraint(AbstractConstraint):
    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        return bool(view_snapshot.settings.get("magika.enabled"))
