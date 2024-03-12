from __future__ import annotations

from abc import ABC, abstractmethod
from collections import UserDict
from enum import Enum
from typing import TYPE_CHECKING, Any, Generator, KeysView, TypedDict, TypeVar, Union

import sublime

SyntaxLike = Union[str, sublime.Syntax]
WindowId = int
WindowIdAble = Union[WindowId, sublime.Window]

_T = TypeVar("_T")


class ListenerEvent(Enum):
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

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def from_value(cls, value: Any) -> ListenerEvent | None:
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


class ST_ConstraintRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    constraint: str
    args: list[Any] | Any | None
    kwargs: dict[str, Any] | None
    inverted: bool


class ST_MatchRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    match: str
    args: list[Any] | Any | None
    kwargs: dict[str, Any] | None
    rules: list[ST_MatchRule | ST_ConstraintRule]  # type: ignore


class ST_SyntaxRule(ST_MatchRule):
    """Typed dict for corresponding ST settings."""

    comment: str
    selector: str
    syntaxes: str | list[str]
    on_events: str | list[str] | None


# `UserDict` is not subscriptable until Python 3.9...
if TYPE_CHECKING:

    class WindowKeyedDict(UserDict[WindowIdAble, _T]):
        def __setitem__(self, key: WindowIdAble, value: _T) -> None: ...

        def __getitem__(self, key: WindowIdAble) -> _T: ...

        def __delitem__(self, key: WindowIdAble) -> None: ...

        def keys(self) -> KeysView[WindowId]: ...
        @staticmethod
        def _to_window_id(value: WindowIdAble) -> WindowId: ...

else:

    class WindowKeyedDict(UserDict):
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
