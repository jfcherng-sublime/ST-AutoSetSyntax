from ...settings import get_merged_plugin_setting
from ..constraint import AbstractConstraint
from typing import final
import sublime


@final
class IsGuesslangEnabledConstraint(AbstractConstraint):
    def test(self, view: sublime.View) -> bool:
        return get_merged_plugin_setting("guesslang.enabled", False, window=view.window())
