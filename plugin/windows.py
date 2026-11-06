import traceback
from collections.abc import Iterable
from typing import Any

import sublime

from .constants import PLUGIN_NAME
from .constants import PY_VERSION
from .constants import ST_CHANNEL
from .constants import ST_PLATFORM_ARCH
from .constants import ST_VERSION
from .constants import VERSION
from .logger import Logger
from .magika import get_magika_object
from .rules import SyntaxRuleCollection
from .rules import get_constraints
from .rules import get_matches
from .settings import pref_syntax_rules
from .shared import G
from .types import DroppedRule
from .utils import stringify


def set_up_window(window: sublime.Window) -> None:
    Logger.log(f"🤠 Howdy! This is {PLUGIN_NAME} {VERSION}. (Panel for {window})", window=window)
    Logger.log(
        f"🌱 Environment: ST {ST_VERSION} {ST_CHANNEL} build with Python {PY_VERSION} ({ST_PLATFORM_ARCH})",
        window=window,
    )
    if magika_obj := get_magika_object():
        Logger.log(
            f"🔮 Magika is available. (v{magika_obj.get_module_version()} / {magika_obj.get_model_name()})",
            window=window,
        )
    compile_rules(window)
    Logger.log("🎉 Plugin is ready now!", window=window)


def tear_down_window(window: sublime.Window) -> None:
    G.syntax_rule_collections.pop(window, None)
    G.dropped_rules_collection.pop(window, None)
    Logger.log("👋 Bye!", window=window)
    Logger.destroy(window=window)


def compile_rules(window: sublime.Window, *, is_update: bool = False) -> None:
    def names_as_str(items: Iterable[Any], *, sep: str = ", ") -> str:
        return sep.join(item.name() for item in items)

    Logger.log(
        f"# {Logger.DELIMITER} re-compile rules for {window} {Logger.DELIMITER} BEGIN",
        window=window,
        enabled=is_update,
    )

    Logger.log(f'🔍 Found "Match" implementations: {names_as_str(get_matches())}', window=window)
    Logger.log(f'🔍 Found "Constraint" implementations: {names_as_str(get_constraints())}', window=window)

    syntax_rules, invalid_rules = pref_syntax_rules(window=window)
    for invalid_rule in invalid_rules:
        Logger.log(f"❌ Ignoring a syntax rule, {invalid_rule.reason}", window=window)

    syntax_rule_collection = SyntaxRuleCollection.make(syntax_rules)
    Logger.log(f"📜 Compiled syntax rule collection: {stringify(syntax_rule_collection)}", window=window)

    # explain each rule as it's discarded: "dropped" alone is ambiguous now that a rule can be
    # discarded for always matching as well as for never matching
    try:
        dropped_rules = [*invalid_rules, *map(DroppedRule.make, syntax_rule_collection.optimize())]
    except Exception:
        # `optimize()` prunes the tree as it walks it, so a pass that dies halfway leaves a half-pruned
        # tree. Rebuild from the source settings: unoptimized rules still test correctly. The likely
        # culprit is a custom `fold()` returning a non-`Fold`, which must not cost the window every other
        # rule; the traceback is logged because it names that class.
        Logger.log(
            f"❌ Failed optimizing the syntax rules, keeping them unoptimized:\n{traceback.format_exc()}",
            window=window,
        )
        syntax_rule_collection = SyntaxRuleCollection.make(syntax_rules)
        dropped_rules = list(invalid_rules)

    G.syntax_rule_collections[window] = syntax_rule_collection
    G.dropped_rules_collection[window] = dropped_rules
    Logger.log(f"✨ Optimized syntax rule collection: {stringify(syntax_rule_collection)}", window=window)
    Logger.log(f"💀 Dropped rules: {stringify(dropped_rules)}", window=window)

    Logger.log(
        f"# {Logger.DELIMITER} re-compile rules for {window} {Logger.DELIMITER} END",
        window=window,
        enabled=is_update,
    )


def ensure_window_set_up(window: sublime.Window) -> None:
    """
    ST fires `on_new(view)` before `on_new_window(window)` for a brand new window's first tab,
    so `on_new` must make sure the window's rules are compiled before evaluating that view.
    """
    if window not in G.syntax_rule_collections:
        set_up_window(window)
