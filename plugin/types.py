from abc import ABC
from abc import abstractmethod
from collections import UserDict
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import KeysView
from enum import StrEnum
from typing import Any
from typing import overload

import sublime
from more_itertools import always_iterable
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

type Comparator = Callable[[Any, Any], bool]
type SyntaxLike = str | sublime.Syntax
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


class Optimizable(ABC):
    def is_droppable(self) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def optimize(self) -> Generator[Any]:
        """Does optimizations and returns a generator for dropped objects."""


class StConstraintRule(BaseModel):
    """Model for a "constraint rule" in settings."""

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


StMatchRule.model_rebuild()


class WindowKeyedDict[VT](UserDict[WindowIdAble, VT]):
    def __contains__(self, key: Any) -> bool:
        key = self._to_window_id(key)
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
        return self.data.keys()  # type: ignore

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
