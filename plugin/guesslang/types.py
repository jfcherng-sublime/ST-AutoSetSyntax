from __future__ import annotations

from typing import List, Optional, TypedDict


class GuesslangServerResponse(TypedDict):
    id: int
    """The message ID, which is an ID of a view actually."""
    data: List[GuesslangServerPredictionItem]
    event_name: Optional[str]


class GuesslangServerPredictionItem(TypedDict):
    languageId: str
    confidence: float
