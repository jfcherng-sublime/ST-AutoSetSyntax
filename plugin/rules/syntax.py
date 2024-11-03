from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass

import sublime
from more_itertools import first_true
from typing_extensions import Self

from ..constants import VERSION
from ..snapshot import ViewSnapshot
from ..types import ListenerEvent, Optimizable, StSyntaxRule
from ..utils import drop_falsy, find_syntax_by_syntax_likes
from .match import MatchRule


@dataclass
class SyntaxRule(Optimizable):
    comment: str = ""
    syntax: sublime.Syntax | None = None
    syntaxes_name: tuple[str, ...] | None = tuple()
    selector: str = "text.plain"
    on_events: set[ListenerEvent] | None = None
    """`None` = no restriction, empty = no event = never triggered."""
    root_rule: MatchRule | None = None

    src_setting: StSyntaxRule | None = None
    """The source setting object."""

    def is_droppable(self) -> bool:
        return not (self.syntax and (self.on_events is None or self.on_events) and self.root_rule)

    def optimize(self) -> Generator[Optimizable, None, None]:
        if self.root_rule:
            if self.root_rule.is_droppable():
                yield self.root_rule
                self.root_rule = None
            else:
                yield from self.root_rule.optimize()
                if self.root_rule.is_droppable():
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
        obj = cls()
        obj.src_setting = syntax_rule

        obj.syntaxes_name = tuple(syntax_rule.syntaxes)
        if target_syntax := find_syntax_by_syntax_likes(syntax_rule.syntaxes):
            obj.syntax = target_syntax

        # note that an empty string selector should match any scope
        obj.selector = syntax_rule.selector

        if (on_events := syntax_rule.on_events) is not None:
            obj.on_events = set(drop_falsy(map(ListenerEvent.from_value, on_events)))

        if match_rule_compiled := MatchRule.make(syntax_rule):
            obj.root_rule = match_rule_compiled

        return obj


@dataclass
class SyntaxRuleCollection(Optimizable):
    version: str = VERSION
    rules: tuple[SyntaxRule, ...] = tuple()

    def __len__(self) -> int:
        return len(self.rules)

    def optimize(self) -> Generator[Optimizable, None, None]:
        rules: list[SyntaxRule] = []
        for rule in self.rules:
            if rule.is_droppable():
                yield rule
                continue
            yield from rule.optimize()
            if rule.is_droppable():
                yield rule
                continue
            rules.append(rule)
        self.rules = tuple(rules)

    def test(self, view_snapshot: ViewSnapshot, event: ListenerEvent | None = None) -> SyntaxRule | None:
        return first_true(self.rules, pred=lambda rule: rule.test(view_snapshot, event))

    @classmethod
    def make(cls, syntax_rules: Iterable[StSyntaxRule]) -> Self:
        """Build this object with the `syntax_rules`."""
        obj = cls()
        obj.rules = tuple(map(SyntaxRule.make, syntax_rules))
        return obj
