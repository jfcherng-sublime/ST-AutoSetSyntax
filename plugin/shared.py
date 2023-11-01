from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

import sublime

from .guesslang.server import GuesslangServer
from .settings import get_merged_plugin_settings
from .snapshot import ViewSnapshotCollection
from .types import Optimizable, WindowKeyedDict

if TYPE_CHECKING:
    from .guesslang.client import GuesslangClient
    from .rules import SyntaxRuleCollection

DroppedRules = List[Optimizable]
DroppedRulesArg = Iterable[Optimizable]

# `UserDict` is not subscriptable until Python 3.9...
if TYPE_CHECKING:
    _WindowKeyedDict_DroppedRules = WindowKeyedDict[DroppedRules]
    _WindowKeyedDict_SyntaxRuleCollection = WindowKeyedDict[SyntaxRuleCollection]
else:
    _WindowKeyedDict_DroppedRules = WindowKeyedDict
    _WindowKeyedDict_SyntaxRuleCollection = WindowKeyedDict


class DroppedRulesCollection(_WindowKeyedDict_DroppedRules):
    pass


class SyntaxRuleCollections(_WindowKeyedDict_SyntaxRuleCollection):
    pass


class G:
    """This class holds "G"lobal variables as its class variables."""

    guesslang_client: GuesslangClient | None = None
    """The guesslang client object, which interacts with the Node.js guesslang server."""

    guesslang_server: GuesslangServer | None = None
    """The guesslang server object."""

    startup_views: set[sublime.View] = set()
    """Views exist before this plugin is loaded when Sublime Text just starts."""

    syntax_rule_collections = SyntaxRuleCollections()
    """The compiled per-window top-level plugin rules."""

    dropped_rules_collection = DroppedRulesCollection()
    """Those per-window rules which are dropped after doing optimizations."""

    view_snapshot_collection = ViewSnapshotCollection()
    """Caches of view attributes."""

    @classmethod
    def is_plugin_ready(cls, window: sublime.Window) -> bool:
        return bool(get_merged_plugin_settings(window=window) and cls.syntax_rule_collections.get(window))
