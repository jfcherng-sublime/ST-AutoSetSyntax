from abc import ABC
from abc import abstractmethod
from collections import UserDict
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import KeysView
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing import Final
from typing import NamedTuple
from typing import Self
from typing import overload

import sublime
from more_itertools import always_iterable
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

type Comparator = Callable[[Any, Any], bool]
type SyntaxLike = str | sublime.Syntax
type SyntaxLikes = SyntaxLike | Iterable[SyntaxLike]
"""One or more `SyntaxLike`. A bare `str` is one "like", never an iterable of characters."""
type WindowId = int
type WindowIdAble = WindowId | sublime.Window

NULL_SYNTAX = sublime.Syntax("", "", False, "")
"""A "null" syntax object for writing cleaner codes."""


class ListenerEvent(StrEnum):
    """Events used in AutoSetSyntax."""

    COMMAND = "command"
    EXEC = "exec"
    INIT = "init"
    LOAD = "load"
    MODIFY = "modify"
    NEW = "new"
    PASTE = "paste"
    RELOAD = "reload"
    REVERT = "revert"
    SAVE = "save"
    UNTRANSIENTIZE = "untransientize"


class Fold(NamedTuple):
    """The constant a rule's `test()` always returns, paired with why it's constant."""

    value: bool | None
    """The constant `test()` always returns, or `None` when the result still depends on the view."""
    reason: str
    """
    Why it's constant, in the user's terms ("no extensions given", not "self.exts is empty") --
    this is what the dropped-rules report shows. Empty when `value` is `None`.
    """


UNFOLDED: Final = Fold(None, "")
"""The result still depends on the view, so there is nothing to explain."""


def _explain(verdict: str, reason: str) -> str:
    """Join a verdict with its reason, tolerating a `fold()` that gave no reason."""
    return f"{verdict}: {reason}" if reason else verdict


class Optimizable(ABC):
    def fold(self) -> Fold:
        """
        The constant this object's `test()` always returns and why, or `UNFOLDED` when the result
        still depends on the view.

        An object folds once its outcome no longer depends on runtime data -- a leaf constraint
        with no arguments, an empty `any`/`all` match, and so on. Whoever holds it uses this to
        decide whether it can be discarded, which needs *which* constant it folds to, not just
        that it folds: an empty `all` is a constant `True` (`all([]) == True`) while an empty
        `any` is a constant `False`, and they are not interchangeable. See
        `AbstractMatch.prunable_child_value()` for what a parent match does with the answer.

        The reason travels with the value because only the folding node knows it: by the time
        `DroppedRule` reports the rule to the user, "never matches" is all that's left to say.

        Defaults to `UNFOLDED` -- "still depends on the view", i.e. never dropped.
        """
        return UNFOLDED

    @abstractmethod
    def optimize(self) -> Generator[Optimizable]:
        """Does optimizations and returns a generator for dropped objects."""


@dataclass(frozen=True, slots=True)
class DroppedRule:
    """A rule discarded during optimizing, paired with why it could be."""

    reason: str
    """Human-readable, for the debug dump -- nothing branches on this. Declared before `rule`
    so it stays readable at the front of the (long) generated repr."""
    rule: Optimizable

    @classmethod
    def make(cls, rule: Optimizable) -> Self:
        """Explain a rule that optimizing has just decided to discard."""
        match rule.fold():
            case Fold(True, reason):
                return cls(_explain("always matches", reason), rule)
            case Fold(False, reason):
                return cls(_explain("never matches", reason), rule)
            case _:
                # optimizing only discards a rule that folds, so this means someone dropped a
                # rule for another reason and didn't say which -- report it rather than lie
                return cls("dropped without folding", rule)


class StConstraintRule(BaseModel):
    """Model for a "constraint rule" in settings."""

    # reject unrecognized keys instead of silently ignoring them: a typo'd key (e.g.
    # "constrait") would otherwise fail this model and quietly validate as a no-op StMatchRule
    # instead (the `rules` union tries StConstraintRule first, then StMatchRule, whose every
    # field has a default), silently dropping the user's rule with no diagnostic at all.
    model_config = ConfigDict(extra="forbid")

    constraint: str
    """The name of the "constraint"."""
    args: list[Any] = Field(default_factory=list)
    """Positional arguments for the "constraint"."""
    kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments for the "constraint"."""
    inverted: bool = False
    """Whether the test result should be inverted."""


class StMatchRule(BaseModel):
    """Model for a "match rule" in settings."""

    # see StConstraintRule.model_config for why this must reject unrecognized keys
    model_config = ConfigDict(extra="forbid")

    match: str = "any"
    """The name of the "match"."""
    args: list[Any] = Field(default_factory=list)
    """Positional arguments for the "match"."""
    kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments for the "match"."""
    rules: list[StConstraintRule | StMatchRule] = Field(default_factory=list)
    """Rules to match against."""


class StSyntaxRule(StMatchRule):
    """Model for a "syntax rule" in settings."""

    comment: str = ""
    """A comment for the rule."""
    selector: str = "text.plain"
    """To constrain the syntax scope of the current view. An empty string matches any scope."""
    syntaxes: list[str] = Field(default_factory=list)
    """Syntaxes to be used. The first available one will be used."""
    on_events: list[str] | None = None
    """Events to listen to, or `None` for all events."""

    @field_validator("syntaxes", "on_events", mode="before")
    @classmethod
    def str_to_list_str(cls, v: Any) -> list[str]:
        return list(always_iterable(v, base_type=str))


class WindowKeyedDict[VT](UserDict[WindowIdAble, VT]):
    def __contains__(self, key: object) -> bool:
        if isinstance(key, sublime.Window):
            key = key.id()
        return key in self.data

    def __delitem__(self, key: WindowIdAble) -> None:
        key = self._to_window_id(key)
        del self.data[key]

    def __getitem__(self, key: WindowIdAble) -> VT:
        key = self._to_window_id(key)
        return self.data[key]

    def __setitem__(self, key: WindowIdAble, value: VT) -> None:
        key = self._to_window_id(key)
        self.data[key] = value

    def keys(self) -> KeysView[WindowId]:
        return self.data.keys()  # type: ignore[return-value]

    @overload
    def get(self, key: WindowIdAble, default: None = None) -> VT | None: ...
    @overload
    def get[T](self, key: WindowIdAble, default: T) -> VT | T: ...
    def get[T](self, key: WindowIdAble, default: T | VT | None = None) -> VT | T | None:
        key = self._to_window_id(key)
        return self.data.get(key, default)

    @staticmethod
    def _to_window_id(value: WindowIdAble) -> WindowId:
        return value.id() if isinstance(value, sublime.Window) else value
