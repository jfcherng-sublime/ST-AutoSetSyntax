from __future__ import annotations

from typing import List, Optional, TypedDict

MODEL_VSCODE_LANGUAGEDETECTION = "vscode-languagedetection"
MODEL_VSCODE_REGEXP_LANGUAGEDETECTION = "vscode-regexp-languagedetection"


class GuesslangServerResponse(TypedDict):
    id: int  # the message ID, which is an ID of a view actually
    data: List[GuesslangServerPredictionItem]
    event_name: Optional[str]


class GuesslangServerPredictionItem(TypedDict):
    languageId: str
    confidence: float
