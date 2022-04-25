from __future__ import annotations

# __future__ must be the first import
from ..helper import camel_to_snake
from ..helper import first
from ..helper import get_all_subclasses
from ..helper import remove_suffix
from ..lru_cache import clearable_lru_cache
from ..types import Optimizable, ST_MatchRule
from .constraint import ConstraintRule
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any, Dict, Generator, List, Optional, Tuple, Type, Union
import sublime


def find_match(obj: Any) -> Optional[Type[AbstractMatch]]:
    return first(get_matches(), lambda t: t.is_supported(obj))


@clearable_lru_cache()
def get_matches() -> Tuple[Type[AbstractMatch], ...]:
    return tuple(
        sorted(
            get_all_subclasses(AbstractMatch, skip_abstract=True),  # type: ignore
            key=lambda cls: cls.name(),
        )
    )


@dataclass
class MatchRule(Optimizable):
    DEFAULT_MATCH_NAME = "any"

    match: Optional[AbstractMatch] = None
    match_name: str = ""
    args: Tuple[Any, ...] = tuple()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    rules: Tuple[MatchableRule, ...] = tuple()

    def is_droppable(self) -> bool:
        return not (self.rules and self.match and not self.match.is_droppable(self.rules))

    def optimize(self) -> Generator[Optimizable, None, None]:
        rules: List[MatchableRule] = []
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

    def test(self, view: sublime.View) -> bool:
        assert self.match
        return self.match.test(view, self.rules)

    @classmethod
    def make(cls, match_rule: ST_MatchRule) -> MatchRule:
        """Build this object with the `match_rule`."""
        obj = cls()

        if args := match_rule.get("args"):
            # make sure args is always a tuple
            obj.args = tuple(args) if isinstance(args, list) else (args,)

        if kwargs := match_rule.get("kwargs"):
            obj.kwargs = kwargs

        match = match_rule.get("match", cls.DEFAULT_MATCH_NAME)
        if match_class := find_match(match):
            obj.match_name = match
            obj.match = match_class(*obj.args, **obj.kwargs)

        rules_compiled: List[MatchableRule] = []
        for rule in match_rule.get("rules", []):
            rule_class: Optional[Type[MatchableRule]] = None
            if "constraint" in rule:
                rule_class = ConstraintRule
            elif "rules" in rule:  # nested MatchRule
                rule_class = MatchRule
            if rule_class and (rule_compiled := rule_class.make(rule)):  # type: ignore
                rules_compiled.append(rule_compiled)
        obj.rules = tuple(rules_compiled)

        return obj


# rules that can be used in a match rule
MatchableRule = Union[ConstraintRule, MatchRule]


class AbstractMatch(metaclass=ABCMeta):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def name(cls) -> str:
        """The nickname of this class. Converts "FooBarMatch" into "foo_bar" by default."""
        return camel_to_snake(remove_suffix(cls.__name__, "Match"))

    @classmethod
    def is_supported(cls, obj: Any) -> bool:
        """Determines whether this class supports `obj`."""
        return str(obj) == cls.name()

    def is_droppable(self, rules: Tuple[MatchableRule, ...]) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def test(self, view: sublime.View, rules: Tuple[MatchableRule, ...]) -> bool:
        """Tests whether the `view` passes this `match` with those `rules`."""
        ...

    @staticmethod
    def test_count(view: sublime.View, rules: Tuple[MatchableRule, ...], goal: float) -> bool:
        """Tests whether the amount of passing `rules` is greater than or equal to `goal`."""
        if goal <= 0:
            return True

        tolerance = len(rules) - goal  # how many rules can be failed at most
        for rule in rules:
            if tolerance < 0:
                return False
            if rule.test(view):
                goal -= 1
                if goal == 0:
                    return True
            else:
                tolerance -= 1
        return False
