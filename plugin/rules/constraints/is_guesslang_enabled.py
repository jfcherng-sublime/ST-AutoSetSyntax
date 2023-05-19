from __future__ import annotations

from typing import final

import sublime

from ...settings import get_merged_plugin_setting
from ..constraint import AbstractConstraint


@final
class IsGuesslangEnabledConstraint(AbstractConstraint):
    def test(self, view: sublime.View) -> bool:
        return bool(get_merged_plugin_setting("guesslang.enabled", False, window=view.window()))
