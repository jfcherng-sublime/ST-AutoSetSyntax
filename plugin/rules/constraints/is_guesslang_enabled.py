from ...settings import get_merged_plugin_setting
from ..constraint import AbstractConstraint
import sublime


class isGuesslangEnabledConstraint(AbstractConstraint):
    def test(self, view: sublime.View) -> bool:
        return get_merged_plugin_setting("guesslang.enabled", False, window=view.window())
