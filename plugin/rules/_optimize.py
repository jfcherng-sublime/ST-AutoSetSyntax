from ..types import Optimizable


def sift_optimizable[T: Optimizable](rules: tuple[T, ...]) -> tuple[list[Optimizable], tuple[T, ...]]:
    """Filter droppable rules and recurse-optimize survivors.

    Returns a tuple of (dropped_rules, surviving_rules).
    """
    dropped: list[Optimizable] = []
    survivors: list[T] = []
    for rule in rules:
        if rule.is_droppable():
            dropped.append(rule)
            continue
        dropped.extend(rule.optimize())
        if rule.is_droppable():
            dropped.append(rule)
            continue
        survivors.append(rule)
    return dropped, tuple(survivors)
