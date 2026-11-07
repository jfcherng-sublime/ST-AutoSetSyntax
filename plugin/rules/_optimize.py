from typing import Any

from ..types import Fold
from ..types import Optimizable
from ..utils import get_fqcn


def require_fold(owner: Any, fold: Any) -> Fold:
    """
    Check what `owner.fold()` returned, naming `owner` when it isn't a `Fold`.

    Nothing else counts -- not a bare `bool`/`None`, not a plain `(value, reason)` tuple that
    happens to have the right shape. Rejecting here rather than at the unpack is what makes the
    failure actionable: "cannot unpack non-iterable bool object" blames this module and never
    says whose `fold()` produced it, and the class name is the only part a user can do anything
    about.
    """
    if isinstance(fold, Fold):
        return fold
    raise TypeError(f"{get_fqcn(owner)}.fold() must return a Fold or UNFOLDED, got {fold!r}")


def sift_optimizable[T: Optimizable](rules: tuple[T, ...]) -> tuple[list[Optimizable], tuple[T, ...]]:
    """Filter rules that fold to a constant and recurse-optimize survivors.

    Returns a tuple of (dropped_rules, surviving_rules).
    """
    dropped: list[Optimizable] = []
    survivors: list[T] = []
    for rule in rules:
        if rule.fold().value is None:
            # only a rule that isn't already a constant is worth recursing into -- and doing so
            # can collapse it into one, hence the second `fold()` below rather than an `else`
            dropped.extend(rule.optimize())
        if rule.fold().value is None:
            survivors.append(rule)
        else:
            dropped.append(rule)
    return dropped, tuple(survivors)
