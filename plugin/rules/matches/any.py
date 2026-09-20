from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class AnyMatch(AbstractMatch):
    """Matches when any rule is matched."""

    @override
    def fold(self, rules: tuple[MatchableRule, ...]) -> bool | None:
        """`any([])` is `False`, so an empty `any` is a constant False -- unlike an empty `all`, which is True."""
        return False if not rules else None

    # prunable_child_value() is intentionally NOT overridden: False is OR's identity element
    # (`any(False, x) == any(x)`), which matches `AbstractMatch`'s inherited default exactly.

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return any(rule.test(view_snapshot) for rule in rules)
