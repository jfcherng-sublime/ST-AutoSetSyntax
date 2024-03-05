from __future__ import annotations

from typing import final

from ...settings import get_merged_plugin_setting
from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsMagikaEnabledConstraint(AbstractConstraint):
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not ((view := view_snapshot.valid_view) and (window := view.window())):
            return False
        return bool(get_merged_plugin_setting("magika.enabled", False, window=window))
