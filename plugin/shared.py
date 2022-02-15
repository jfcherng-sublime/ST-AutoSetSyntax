from .guesslang.client import GuesslangClient
from .rules import SyntaxRuleCollection
from .settings import get_merged_plugin_settings
from typing import Any, Dict, Optional, Tuple
import sublime

WindowId = int
DroppedRules = Tuple[Any, ...]


class G:
    """This class holds "G"lobal variables as its class variables."""

    # the guesslang object, which interacts with the Node.js guesslang server
    guesslang: Optional[GuesslangClient] = None

    # views exist when ST just starts (even before plugin loaded)
    views_on_init: Tuple[sublime.View, ...] = tuple()

    # per window, the compiled top-level plugin rules
    windows_syntax_rule_collection: Dict[WindowId, SyntaxRuleCollection] = {}

    # per window, those rules which are dropped after doing optimizations
    windows_dropped_rules: Dict[WindowId, DroppedRules] = {}

    @classmethod
    def is_plugin_ready(cls, window: sublime.Window) -> bool:
        return bool(get_merged_plugin_settings(window=window) and cls.get_syntax_rule_collection(window))

    @classmethod
    def set_syntax_rule_collection(cls, window: sublime.Window, value: SyntaxRuleCollection) -> None:
        cls.windows_syntax_rule_collection[window.id()] = value

    @classmethod
    def get_syntax_rule_collection(cls, window: sublime.Window) -> Optional[SyntaxRuleCollection]:
        return cls.windows_syntax_rule_collection.get(window.id())

    @classmethod
    def remove_syntax_rule_collection(cls, window: sublime.Window) -> Optional[SyntaxRuleCollection]:
        return cls.windows_syntax_rule_collection.pop(window.id(), None)

    @classmethod
    def set_dropped_rules(cls, window: sublime.Window, value: DroppedRules) -> None:
        cls.windows_dropped_rules[window.id()] = value

    @classmethod
    def get_dropped_rules(cls, window: sublime.Window) -> DroppedRules:
        return cls.windows_dropped_rules.get(window.id()) or tuple()

    @classmethod
    def remove_dropped_rules(cls, window: sublime.Window) -> Optional[DroppedRules]:
        return cls.windows_dropped_rules.pop(window.id(), None)
