from _typeshed import Incomplete
from magika.strenum import LowerCaseStrEnum as LowerCaseStrEnum
from typing import List

class PredictionMode(LowerCaseStrEnum):
    BEST_GUESS: Incomplete
    MEDIUM_CONFIDENCE: Incomplete
    HIGH_CONFIDENCE: Incomplete
    @staticmethod
    def get_valid_prediction_modes() -> List[str]: ...
