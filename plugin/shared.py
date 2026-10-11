from dataclasses import dataclass
from dataclasses import field

import sublime

from .rules import SyntaxRuleCollection
from .settings import get_merged_plugin_settings
from .types import DroppedRule
from .types import WindowKeyedDict

type DroppedRules = list[DroppedRule]

DroppedRulesCollection = WindowKeyedDict[DroppedRules]
SyntaxRuleCollections = WindowKeyedDict[SyntaxRuleCollection]


@dataclass(slots=True)
class _GlobalState:
    startup_views: set[sublime.View] = field(default_factory=set)
    """Views exist before this plugin is loaded when Sublime Text just starts."""

    syntax_rule_collections: SyntaxRuleCollections = field(default_factory=SyntaxRuleCollections)
    """The compiled per-window top-level plugin rules."""

    dropped_rules_collection: DroppedRulesCollection = field(default_factory=DroppedRulesCollection)
    """Those per-window rules which are dropped after doing optimizations."""

    def is_plugin_ready(self, window: sublime.Window) -> bool:
        # an empty collection is still a compiled one (every rule may have been optimized away),
        # so test membership rather than truthiness: `SyntaxRuleCollection.__len__` makes an empty
        # collection falsy
        return bool(get_merged_plugin_settings(window=window)) and window in self.syntax_rule_collections


G = _GlobalState()
