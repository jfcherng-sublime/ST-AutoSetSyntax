from __future__ import annotations

# __future__ must be the first import
from typing import List, Optional, TypedDict


class GuesslangServerResponse(TypedDict):
    id: int  # the message ID, which is an ID of a view actually
    data: List[GuesslangServerPredictionItem]
    event_name: Optional[str]


class GuesslangServerPredictionItem(TypedDict):
    languageId: str
    confidence: float
