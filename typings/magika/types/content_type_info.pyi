from dataclasses import dataclass
from magika.logger import get_logger as get_logger
from magika.types.content_type_label import ContentTypeLabel as ContentTypeLabel

@dataclass(frozen=True)
class ContentTypeInfo:
    label: ContentTypeLabel
    mime_type: str
    group: str
    description: str
    extensions: list[str]
    is_text: bool
    @property
    def ct_label(self) -> str: ...
    @property
    def score(self) -> float: ...
    @property
    def magic(self) -> str: ...
    def __init__(self, label, mime_type, group, description, extensions, is_text) -> None: ...
