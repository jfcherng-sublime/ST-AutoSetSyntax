from collections.abc import Generator
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self
from typing import override

import sublime
from more_itertools import first_true
from more_itertools import map_except

from ..constants import VERSION
from ..snapshot import ViewSnapshot
from ..types import UNFOLDED
from ..types import Fold
from ..types import ListenerEvent
from ..types import Optimizable
from ..types import StSyntaxRule
from ..utils import find_syntax
from ..utils import quote_join
from ._optimize import sift_optimizable
from .match import MatchRule


@dataclass(slots=True)
class SyntaxRule(Optimizable):
    comment: str = ""
    syntax: sublime.Syntax | None = None
    syntaxes_name: tuple[str, ...] | None = ()
    selector: str = "text.plain"
    on_events: set[ListenerEvent] | None = None
    """`None` = no restriction, empty = no event = never triggered."""
    root_rule: MatchRule | None = None

    src_setting: StSyntaxRule | None = None
    """The source setting object."""

    @override
    def fold(self) -> Fold:
        # with no syntax to assign, no event that can ever trigger it, or no root rule left,
        # this rule can never usefully match
        if not self.syntax:
            return Fold(False, f"none of these syntaxes is available: {quote_join(self.syntaxes_name or ())}")
        if self.on_events is not None and not self.on_events:
            return Fold(False, '"on_events" lists no event that could trigger it')
        if not self.root_rule:
            return Fold(False, "no sub-rule is left to test")
        return UNFOLDED

    @override
    def optimize(self) -> Generator[Optimizable]:
        if not self.root_rule:
            return

        if (folded := self.root_rule.fold().value) is None:
            yield from self.root_rule.optimize()
            folded = self.root_rule.fold().value  # optimizing may have collapsed it to a constant

        # a constant-True root_rule always matches (given selector/events); only a
        # constant-False one can be discarded without changing this rule's behavior
        if folded is False:
            yield self.root_rule
            self.root_rule = None

    def test(self, view_snapshot: ViewSnapshot, event: ListenerEvent | None = None) -> bool:
        if event and self.on_events is not None and event not in self.on_events:
            return False

        if not view_snapshot.syntax:
            return False

        # note that an empty selector matches anything
        if sublime.score_selector(view_snapshot.syntax.scope, self.selector) == 0:
            return False

        assert self.root_rule
        return self.root_rule.test(view_snapshot)

    @classmethod
    def make(cls, syntax_rule: StSyntaxRule) -> Self:
        """Build this object with the `syntax_rule`."""
        this = cls()
        this.src_setting = syntax_rule

        this.syntaxes_name = tuple(syntax_rule.syntaxes)
        if target_syntax := find_syntax(syntax_rule.syntaxes, include_hidden=True):
            this.syntax = target_syntax

        this.comment = syntax_rule.comment
        # note that an empty string selector should match any scope
        this.selector = syntax_rule.selector

        if (on_events := syntax_rule.on_events) is not None:
            this.on_events = set(map_except(ListenerEvent, on_events, ValueError))

        if match_rule_compiled := MatchRule.make(syntax_rule):
            this.root_rule = match_rule_compiled

        return this


@dataclass(slots=True)
class SyntaxRuleCollection(Optimizable):
    version: str = VERSION
    rules: tuple[SyntaxRule, ...] = ()

    def __len__(self) -> int:
        return len(self.rules)

    @override
    def optimize(self) -> Generator[Optimizable]:
        dropped, self.rules = sift_optimizable(self.rules)
        yield from dropped

    def test(self, view_snapshot: ViewSnapshot, event: ListenerEvent | None = None) -> SyntaxRule | None:
        return first_true(self.rules, pred=lambda rule: rule.test(view_snapshot, event))

    @classmethod
    def make(cls, syntax_rules: Iterable[StSyntaxRule]) -> Self:
        """Build this object with the `syntax_rules`."""
        return cls(rules=tuple(map(SyntaxRule.make, syntax_rules)))
