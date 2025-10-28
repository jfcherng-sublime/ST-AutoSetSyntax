from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections import UserDict as BuiltinUserDict
from collections.abc import Generator, Hashable, Iterator, KeysView
from enum import Enum
from typing import Any, Generic, TypeVar, Union, overload

import sublime
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Self

SyntaxLike = Union[str, sublime.Syntax]
WindowId = int
WindowIdAble = Union[WindowId, sublime.Window]

_KT = TypeVar("_KT", bound=Hashable)
_KV = TypeVar("_KV")
_T = TypeVar("_T")

if sys.version_info < (3, 9):

    class UserDict(BuiltinUserDict, Generic[_KT, _KV]):
        """Workaround class for the fact that `UserDict` is not subscriptable until Python 3.9..."""

        def __init__(self, dict=None, /, **kwargs) -> None:
            self.data: dict[_KT, _KV] = {}
            super().__init__(dict, **kwargs)

        def __getitem__(self, key: _KT) -> _KV:
            return super().__getitem__(key)

        def __setitem__(self, key: _KT, item: _KV) -> None:
            super().__setitem__(key, item)

        def __delitem__(self, key: _KT) -> None:
            super().__delitem__(key)

        def __iter__(self) -> Iterator[_KT]:
            return super().__iter__()

        @overload
        def get(self, key: _KT) -> _KV | None: ...
        @overload
        def get(self, key: _KT, default: _T) -> _KV | _T: ...
        def get(self, key: _KT, default: _T | None = None) -> _KV | _T | None:
            return super().get(key, default)

else:
    UserDict = BuiltinUserDict  # noqa: F401

if sys.version_info < (3, 11):

    class StrEnum(str, Enum):
        __format__ = str.__format__  # type: ignore
        __str__ = str.__str__  # type: ignore

else:
    from enum import StrEnum  # noqa: F401


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

    @classmethod
    def from_value(cls, value: Any) -> Self | None:
        try:
            return cls(value)
        except ValueError:
            return None


class Optimizable(ABC):
    def is_droppable(self) -> bool:
        """
        Determines whether this object is droppable.
        If it's droppable, then it may be dropped by who holds it during optimizing.
        """
        return False

    @abstractmethod
    def optimize(self) -> Generator[Any, None, None]:
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
        return [v] if isinstance(v, str) else v


class WindowKeyedDict(UserDict[WindowIdAble, _T]):
    def __contains__(self, key: Any) -> bool:
        key = self._to_window_id(key)
        return super().__contains__(key)

    def __setitem__(self, key: WindowIdAble, value: _T) -> None:
        key = self._to_window_id(key)
        super().__setitem__(key, value)

    def __getitem__(self, key: WindowIdAble) -> _T:
        key = self._to_window_id(key)
        return super().__getitem__(key)

    def __delitem__(self, key: WindowIdAble) -> None:
        key = self._to_window_id(key)
        super().__delitem__(key)

    def keys(self) -> KeysView[WindowId]:
        return super().keys()

    @staticmethod
    def _to_window_id(value: WindowIdAble) -> WindowId:
        return value.id() if isinstance(value, sublime.Window) else value
