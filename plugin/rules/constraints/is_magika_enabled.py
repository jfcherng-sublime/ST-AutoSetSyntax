from typing import final
from typing import override

from ...magika import get_magika_object
from ...settings import get_merged_plugin_setting
from ...snapshot import ViewSnapshot
from ..constraint import AbstractConstraint


@final
class IsMagikaEnabledConstraint(AbstractConstraint):
    @override
    def test(self, view_snapshot: ViewSnapshot) -> bool:
        if not ((view := view_snapshot.valid_view) and (window := view.window())):
            return False
        if not get_merged_plugin_setting("magika.enabled", False, window=window):
            return False
        # "enabled" must mean enabled AND actually usable: the library is an optional dependency
        # and its model can fail to initialize. Rules gated on the *inverted* version of this
        # constraint (e.g. the regex-based JS fallback) cover exactly the files Magika would
        # otherwise detect -- reporting True when Magika never runs would leave such files
        # with no syntax at all. Only reached when the user opted in, so the eager model load
        # here is the documented cost of `magika.enabled`, not startup (see set_up_window).
        return get_magika_object() is not None
