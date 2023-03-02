from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple, TypedDict, Union

import sublime

SyntaxLike = Union[str, sublime.Syntax]


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
    def from_value(cls, value: Any) -> Optional[ListenerEvent]:
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
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    inverted: bool


class ST_MatchRule(TypedDict):
    """Typed dict for corresponding ST settings."""

    match: str
    args: Optional[Union[List[Any], Any]]
    kwargs: Optional[Dict[str, Any]]
    rules: List[Union[ST_MatchRule, ST_ConstraintRule]]  # type: ignore


class ST_SyntaxRule(ST_MatchRule):
    """Typed dict for corresponding ST settings."""

    comment: str
    selector: str
    syntaxes: Union[str, List[str]]
    on_events: Optional[Union[str, List[str]]]


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

    def __init__(self, major: Union[int, str] = 0, minor: Union[int, str] = 0, patch: Union[int, str] = 0) -> None:
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)

    @classmethod
    def from_str(cls, version: str) -> Optional[SemanticVersion]:
        try:
            return cls(*version.split("."))
        except Exception:
            return None

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)
