from dataclasses import dataclass
from dataclasses import field

import sublime

from .rules import SyntaxRuleCollection
from .types import DroppedRule
from .types import WindowKeyedDict


@dataclass(frozen=True, slots=True)
class CompiledRules:
    """What compiling one window's settings produced."""

    collection: SyntaxRuleCollection
    """The top-level plugin rules, optimized."""
    dropped: list[DroppedRule]
    """The rules discarded on the way, with why."""


@dataclass(slots=True)
class _GlobalState:
    startup_views: set[sublime.View] = field(default_factory=set)
    """Views exist before this plugin is loaded when Sublime Text just starts."""

    compiled_rules: WindowKeyedDict[CompiledRules] = field(default_factory=WindowKeyedDict)
    """Per window. A window is ready for detection exactly when it has an entry."""


G = _GlobalState()
