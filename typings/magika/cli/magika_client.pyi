from _typeshed import Incomplete
from magika import Magika as Magika, MagikaError as MagikaError, PredictionMode as PredictionMode, colors as colors
from magika.logger import get_logger as get_logger
from magika.types import ContentTypeLabel as ContentTypeLabel, MagikaResult as MagikaResult
from magika.types.overwrite_reason import OverwriteReason as OverwriteReason
from pathlib import Path

VERSION: Incomplete
CONTACT_EMAIL: str
CONTEXT_SETTINGS: Incomplete
HELP_EPILOG: Incomplete

def main(file: list[Path], recursive: bool, json_output: bool, jsonl_output: bool, mime_output: bool, label_output: bool, magic_compatibility_mode: bool, output_score: bool, prediction_mode_str: str, batch_size: int, no_dereference: bool, with_colors: bool, verbose: bool, debug: bool, output_version: bool, model_dir: Path | None) -> None:
    """
    Magika - Determine type of FILEs with deep-learning.
    """
def should_read_from_stdin(files_paths: list[Path]) -> bool: ...
def get_magika_result_from_stdin(magika: Magika) -> MagikaResult: ...
