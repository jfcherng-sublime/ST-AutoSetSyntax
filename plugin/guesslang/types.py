from __future__ import annotations

from enum import Enum
from typing import List, Optional, TypedDict


class DetectorModel(Enum):
    """Programming language detectors used in VSCode."""

    DEFAULT = "vscode-regexp-languagedetection"
    VSCODE_LANGUAGEDETECTION = "vscode-languagedetection"
    VSCODE_REGEXP_LANGUAGEDETECTION = "vscode-regexp-languagedetection"


class GuesslangServerResponse(TypedDict):
    id: int
    """The message ID, which is an ID of a view actually."""
    data: List[GuesslangServerPredictionItem]
    event_name: Optional[str]


class GuesslangServerPredictionItem(TypedDict):
    languageId: str
    confidence: float
