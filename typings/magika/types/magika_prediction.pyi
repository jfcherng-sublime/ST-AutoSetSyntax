from dataclasses import dataclass
from magika.types.content_type_info import ContentTypeInfo as ContentTypeInfo

@dataclass(frozen=True)
class MagikaPrediction:
    dl: ContentTypeInfo
    output: ContentTypeInfo
    score: float
    def __init__(self, dl, output, score) -> None: ...
