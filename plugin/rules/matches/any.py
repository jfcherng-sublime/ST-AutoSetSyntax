from typing import final
from typing import override

from ...snapshot import ViewSnapshot
from ...types import UNFOLDED
from ...types import Fold
from ..match import AbstractMatch
from ..match import MatchableRule


@final
class AnyMatch(AbstractMatch):
    """Matches when any rule is matched."""

    @override
    def fold(self, rules: tuple[MatchableRule, ...]) -> Fold:
        """
        `any([])` is `False`, so an empty `any` is a constant False -- unlike an empty `all`, which
        is True. `True` absorbs OR, so one sub-rule that always matches makes the whole `any` always
        match.
        """
        if not rules:
            return Fold(False, 'an "any" with no sub-rule matches nothing')
        if (child := self.first_child_folding_to(rules, True)) is not None:
            return Fold(True, f'one of its "any" sub-rules always matches: {child.reason}')
        return UNFOLDED

    @override
    def prunable_child_value(self) -> bool | None:
        return False

    @override
    def test(self, view_snapshot: ViewSnapshot, rules: tuple[MatchableRule, ...]) -> bool:
        return any(rule.test(view_snapshot) for rule in rules)
