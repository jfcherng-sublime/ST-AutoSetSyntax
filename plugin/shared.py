from __future__ import annotations

from typing import List

import sublime

from .rules import SyntaxRuleCollection
from .settings import get_merged_plugin_settings
from .types import Optimizable, WindowKeyedDict

_DroppedRules = List[Optimizable]


class DroppedRulesCollection(WindowKeyedDict[_DroppedRules]):
    pass


class SyntaxRuleCollections(WindowKeyedDict[SyntaxRuleCollection]):
    pass


class G:
    """This class holds "G"lobal variables as its class variables."""

    startup_views: set[sublime.View] = set()
    """Views exist before this plugin is loaded when Sublime Text just starts."""

    syntax_rule_collections = SyntaxRuleCollections()
    """The compiled per-window top-level plugin rules."""

    dropped_rules_collection = DroppedRulesCollection()
    """Those per-window rules which are dropped after doing optimizations."""

    @classmethod
    def is_plugin_ready(cls, window: sublime.Window) -> bool:
        return bool(get_merged_plugin_settings(window=window) and cls.syntax_rule_collections.get(window))
