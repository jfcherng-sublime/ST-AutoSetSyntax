from magika.content_types import ContentType as ContentType, ContentTypesManager as ContentTypesManager
from magika.logger import get_logger as get_logger
from magika.prediction_mode import PredictionMode as PredictionMode
from magika.types import MagikaOutputFields as MagikaOutputFields, MagikaResult as MagikaResult, ModelFeatures as ModelFeatures, ModelOutput as ModelOutput, ModelOutputFields as ModelOutputFields
from pathlib import Path
from typing import List, Optional

class Magika:
    def __init__(self, model_dir: Optional[Path] = None, prediction_mode: PredictionMode = ..., no_dereference: bool = False, verbose: bool = False, debug: bool = False, use_colors: bool = False) -> None: ...
    def identify_path(self, path: Path) -> MagikaResult: ...
    def identify_paths(self, paths: List[Path]) -> List[MagikaResult]: ...
    def identify_bytes(self, content: bytes) -> MagikaResult: ...
    @staticmethod
    def get_default_model_name() -> str: ...
    def get_model_name(self) -> str: ...

class MagikaError(Exception): ...