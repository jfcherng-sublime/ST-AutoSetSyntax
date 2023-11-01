from __future__ import annotations

from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass
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


@dataclass
class SemanticVersion:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"<SemanticVersion {str(self)}>"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self.to_tuple() == other.to_tuple()

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self.to_tuple() < other.to_tuple()

    def __init__(self, major: int | str = 0, minor: int | str = 0, patch: int | str = 0) -> None:
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)

    @classmethod
    def from_str(cls, version: str) -> SemanticVersion | None:
        try:
            return cls(*version.split("."))
        except Exception:
            return None

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)
