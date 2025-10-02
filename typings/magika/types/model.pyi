from dataclasses import dataclass
from magika.types.content_type_label import ContentTypeLabel as ContentTypeLabel

@dataclass(frozen=True)
class ModelFeatures:
    beg: list[int]
    mid: list[int]
    end: list[int]
    offset_0x8000_0x8007: list[int]
    offset_0x8800_0x8807: list[int]
    offset_0x9000_0x9007: list[int]
    offset_0x9800_0x9807: list[int]

@dataclass(frozen=True)
class ModelOutput:
    label: ContentTypeLabel
    score: float

@dataclass(frozen=True)
class ModelConfig:
    beg_size: int
    mid_size: int
    end_size: int
    use_inputs_at_offsets: bool
    medium_confidence_threshold: float
    min_file_size_for_dl: int
    padding_token: int
    block_size: int
    target_labels_space: list[ContentTypeLabel]
    thresholds: dict[ContentTypeLabel, float]
    overwrite_map: dict[ContentTypeLabel, ContentTypeLabel]
