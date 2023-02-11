from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, Optional, Tuple

import sublime

from .guesslang.server import GuesslangServer
from .settings import get_merged_plugin_settings
from .types import Optimizable

if TYPE_CHECKING:
    from .guesslang.client import GuesslangClient
    from .rules import SyntaxRuleCollection

WindowId = int
DroppedRules = Tuple[Optimizable, ...]
DroppedRulesArg = Iterable[Optimizable]


class G:
    """This class holds "G"lobal variables as its class variables."""

    guesslang: Optional[GuesslangClient] = None
    """The guesslang object, which interacts with the Node.js guesslang server."""

    guesslang_server: Optional[GuesslangServer] = None
    """The guesslang server object."""

    views_on_init: Tuple[sublime.View, ...] = tuple()
    """Views exist when ST just starts (even before plugin loaded)."""

    windows_syntax_rule_collection: Dict[WindowId, SyntaxRuleCollection] = {}
    """Per window, the compiled top-level plugin rules."""

    windows_dropped_rules: Dict[WindowId, DroppedRules] = {}
    """Per window, those rules which are dropped after doing optimizations."""

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
    def clear_syntax_rule_collection(cls, window: sublime.Window) -> Optional[SyntaxRuleCollection]:
        return cls.windows_syntax_rule_collection.pop(window.id(), None)

    @classmethod
    def set_dropped_rules(cls, window: sublime.Window, value: DroppedRulesArg) -> None:
        cls.windows_dropped_rules[window.id()] = tuple(value)

    @classmethod
    def get_dropped_rules(cls, window: sublime.Window) -> DroppedRules:
        return cls.windows_dropped_rules.get(window.id()) or tuple()

    @classmethod
    def clear_dropped_rules(cls, window: sublime.Window) -> Optional[DroppedRules]:
        return cls.windows_dropped_rules.pop(window.id(), None)
