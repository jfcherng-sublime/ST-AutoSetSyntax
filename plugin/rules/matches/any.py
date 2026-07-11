from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class AnyMatch(AbstractMatch):
    """Matches when any rule is matched."""

    @override
    def is_droppable(self, rules: tuple[MatchableRule, ...]) -> bool:
        return len(rules) == 0

    # droppable_value() and prunable_child_value() are intentionally NOT overridden: an empty
    # `any` is a constant False (`any([]) == False`), and False is OR's identity element
    # (`any(False, x) == any(x)`) -- both match `AbstractMatch`'s inherited defaults exactly.

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return any(rule.test(view_snapshot) for rule in rules)
