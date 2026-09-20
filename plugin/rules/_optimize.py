from typing import Any

from ..constants import PLUGIN_NAME
from ..types import Optimizable
from ..utils import list_all_subclasses

_LEGACY_METHOD_NAMES = ("is_droppable", "droppable_value")
"""The methods `fold()` replaced. Overriding one no longer does anything."""


def warn_legacy_fold_overrides(*bases: type[Any]) -> None:
    """
    Warn about custom implementations still overriding the methods `fold()` replaced.

    A custom constraint/match that overrides `is_droppable()`/`droppable_value()` isn't broken
    -- it just silently stops being optimized away, since nothing calls those names any more.
    A silent loss of optimization is a miserable thing to debug, so say so at load time.
    """
    for base in bases:
        for cls in list_all_subclasses(base, skip_self=True):
            if legacy := [name for name in _LEGACY_METHOD_NAMES if name in vars(cls)]:
                print(
                    f"[{PLUGIN_NAME}][WARNING] {cls.__module__}.{cls.__qualname__} overrides"
                    f" {'/'.join(legacy)}, which is no longer used."
                    " Rename it to fold(), returning True/False for a constant result"
                    " or None when the result still depends on the view."
                )


def sift_optimizable[T: Optimizable](rules: tuple[T, ...]) -> tuple[list[Optimizable], tuple[T, ...]]:
    """Filter rules that fold to a constant and recurse-optimize survivors.

    Returns a tuple of (dropped_rules, surviving_rules).
    """
    dropped: list[Optimizable] = []
    survivors: list[T] = []
    for rule in rules:
        if rule.fold() is None:
            # only a rule that isn't already a constant is worth recursing into -- and doing so
            # can collapse it into one, hence the second `fold()` below rather than an `else`
            dropped.extend(rule.optimize())
        if rule.fold() is None:
            survivors.append(rule)
        else:
            dropped.append(rule)
    return dropped, tuple(survivors)
