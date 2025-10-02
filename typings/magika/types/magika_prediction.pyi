from dataclasses import dataclass
from magika.types.content_type_info import ContentTypeInfo as ContentTypeInfo
from magika.types.overwrite_reason import OverwriteReason as OverwriteReason

@dataclass(frozen=True)
class MagikaPrediction:
    dl: ContentTypeInfo
    output: ContentTypeInfo
    score: float
    overwrite_reason: OverwriteReason
