from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections import UserDict as BuiltinUserDict
from collections.abc import Generator, Hashable, Iterator, KeysView
from enum import Enum
from typing import Any, Generic, TypedDict, TypeVar, Union, overload

import sublime
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


class StConstraintRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    constraint: str
    args: list[Any] | Any | None
    kwargs: dict[str, Any] | None
    inverted: bool


class StMatchRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    match: str
    args: list[Any] | Any | None
    kwargs: dict[str, Any] | None
    rules: list[StMatchRule | StConstraintRule]


class StSyntaxRule(StMatchRule):
    """Typed dict for corresponding ST settings."""

    comment: str
    selector: str
    syntaxes: str | list[str]
    on_events: str | list[str] | None


class WindowKeyedDict(UserDict[WindowIdAble, _T]):
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
