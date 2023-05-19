from __future__ import annotations

from typing import TypedDict


class GuesslangServerResponse(TypedDict):
    id: int
    """The message ID, which is an ID of a view actually."""
    data: list[GuesslangServerPredictionItem]
    event_name: str | None


class GuesslangServerPredictionItem(TypedDict):
    languageId: str
    confidence: float
