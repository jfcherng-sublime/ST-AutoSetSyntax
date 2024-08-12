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
    def __init__(self, beg, mid, end, offset_0x8000_0x8007, offset_0x8800_0x8807, offset_0x9000_0x9007, offset_0x9800_0x9807) -> None: ...

@dataclass(frozen=True)
class ModelOutput:
    ct_label: ContentTypeLabel
    score: float
    def __init__(self, ct_label, score) -> None: ...

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
    def __init__(self, beg_size, mid_size, end_size, use_inputs_at_offsets, medium_confidence_threshold, min_file_size_for_dl, padding_token, block_size, target_labels_space, thresholds, overwrite_map) -> None: ...
