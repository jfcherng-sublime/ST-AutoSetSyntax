from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ModelFeatures:
    beg: List[int]
    mid: List[int]
    end: List[int]
    def __init__(self, beg, mid, end) -> None: ...

@dataclass
class ModelOutput:
    ct_label: str
    score: float
    def __init__(self, ct_label, score) -> None: ...

@dataclass
class MagikaResult:
    path: str
    dl: ModelOutputFields
    output: MagikaOutputFields
    def __init__(self, path, dl, output) -> None: ...

@dataclass
class ModelOutputFields:
    ct_label: Optional[str]
    score: Optional[float]
    group: Optional[str]
    mime_type: Optional[str]
    magic: Optional[str]
    description: Optional[str]
    def __init__(self, ct_label, score, group, mime_type, magic, description) -> None: ...

@dataclass
class MagikaOutputFields:
    ct_label: str
    score: float
    group: str
    mime_type: str
    magic: str
    description: str
    def __init__(self, ct_label, score, group, mime_type, magic, description) -> None: ...

@dataclass
class FeedbackReport:
    hash: str
    features: ModelFeatures
    result: MagikaResult
    def __init__(self, hash, features, result) -> None: ...
