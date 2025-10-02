import numpy.typing as npt
import onnxruntime as rt
import os
from _typeshed import Incomplete
from magika.logger import get_logger as get_logger
from magika.types import ContentTypeInfo as ContentTypeInfo, ContentTypeLabel as ContentTypeLabel, MagikaError as MagikaError, MagikaPrediction as MagikaPrediction, MagikaResult as MagikaResult, ModelConfig as ModelConfig, ModelFeatures as ModelFeatures, ModelOutput as ModelOutput, OverwriteReason as OverwriteReason, PredictionMode as PredictionMode, Seekable as Seekable, Status as Status
from pathlib import Path
from typing import BinaryIO, Sequence

_DEFAULT_MODEL_NAME: str

class Magika:
    _log: Incomplete
    _model_dir: Incomplete
    _model_path: Incomplete
    _model_config_path: Incomplete
    _model_config: ModelConfig
    _target_labels_space_np: Incomplete
    _prediction_mode: Incomplete
    _no_dereference: Incomplete
    _cts_infos: Incomplete
    _onnx_session: Incomplete
    def __init__(self, model_dir: Path | None = None, prediction_mode: PredictionMode = ..., no_dereference: bool = False, verbose: bool = False, debug: bool = False, use_colors: bool = False) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def get_module_version(self) -> str: ...
    def get_model_name(self) -> str: ...
    def identify_path(self, path: str | os.PathLike) -> MagikaResult:
        """Identify the content type of a file given its path."""
    def identify_paths(self, paths: Sequence[str | os.PathLike]) -> list[MagikaResult]:
        """Identify the content type of a list of files given their paths."""
    def identify_bytes(self, content: bytes) -> MagikaResult:
        """Identify the content type of raw bytes."""
    def identify_stream(self, stream: BinaryIO) -> MagikaResult:
        """Identify the content type of a BinaryIO stream. Note that this method will
        seek() around the stream."""
    def get_output_content_types(self) -> list[ContentTypeLabel]:
        """This method returns the list of all possible output content types of
        the module. I.e., all possible values for
        `MagikaResult.prediction.output.label`.  This considers the list of
        possible outputs from the model itself, but also keeps into account
        additional configuration such as `override_map` and special content
        types such as `ContentTypeLabel.EMPTY` or `ContentTypeLabel.SYMLINK`.
        """
    def get_model_content_types(self) -> list[ContentTypeLabel]:
        '''This method returns the list of all possible output of the underlying
        model. I.e., all possible values for `MagikaResult.prediction.dl.label`.
        Note that, in general, the list of "model outputs" is different than the
        "tool outputs" as in some cases the model is not even used, or the
        model\'s output is overwritten due to a low-confidence score, or other
        reasons.  This API is useful mostly for debugging purposes; the vast
        majority of client should use `get_output_content_types()`.
        '''
    @staticmethod
    def _get_default_model_name() -> str:
        """This returns the default model name.

        We make this method static so that it can be used by external
        clients/tests without the need to instantiate a Magika object.
        """
    @staticmethod
    def _load_content_types_kb(content_types_kb_json_path: Path) -> dict[ContentTypeLabel, ContentTypeInfo]: ...
    @staticmethod
    def _load_model_config(model_config_path: Path) -> ModelConfig: ...
    def _init_onnx_session(self) -> rt.InferenceSession: ...
    def _get_ct_info(self, content_type: ContentTypeLabel) -> ContentTypeInfo: ...
    def _get_results_from_paths(self, paths: list[Path]) -> list[MagikaResult]:
        """Given a list of paths, returns a list of MagikaResult objects, which
        contain relevant information, such as: file path, the output of the DL
        model, the confidence score, the output of the tool, and associated
        metadata. The order of the predictions matches the order of the input
        paths."""
    def _get_result_from_path(self, path: Path) -> MagikaResult: ...
    def _get_result_from_seekable(self, seekable: Seekable) -> MagikaResult: ...
    @staticmethod
    def _extract_features_from_seekable(seekable: Seekable, beg_size: int, mid_size: int, end_size: int, padding_token: int, block_size: int, use_inputs_at_offsets: bool) -> ModelFeatures:
        '''Extract features from an input seekable.

        This implements features extraction v2 from a seekable, which is an
        abstraction about anything that has a size and that can be "read_at" a
        specific offset, such as a file or a buffer. This is implemented so that
        we do not need to load the entire file in memory or scan the entire
        buffer.

        High-level overview on what we do:
        - We read (at most) `block_size` bytes from the beginning and from the
        end.
        - We normalize these bytes by stripping whitespaces.
        - We consider `beg_size` and `end_size` bytes as `beg` and `end`
        features. If we don\'t have enough bytes, we use `padding_token` as
        padding.

        See comments below for the specifics and handling of corner cases.

        NOTE: This implementation does not support extraction of `mid` features
        and `use_inputs_at_offsets`.
        '''
    @staticmethod
    def _get_beg_ints_with_padding(beg_content: bytes, beg_size: int, padding_token: int) -> list[int]:
        """Take an (already-stripped) buffer as input and extract beg ints.
        This returns a list of integers whose length is exactly beg_size. If
        the buffer is bigger than required, take only the initial portion. If
        the buffer is shorter, add padding at the end.
        """
    @staticmethod
    def _get_end_ints_with_padding(end_content: bytes, end_size: int, padding_token: int) -> list[int]:
        """Take an (already-stripped) buffer as input and extract end ints. This
        returns a list of integers whose length is exactly end_size.  If the
        buffer is bigger than required, take only the last portion. If the
        buffer is shorter, add padding at the beginning.
        """
    def _get_model_outputs_from_features(self, all_features: list[tuple[Path, ModelFeatures]]) -> list[tuple[Path, ModelOutput]]: ...
    def _get_results_from_features(self, all_features: list[tuple[Path, ModelFeatures]]) -> dict[str, MagikaResult]: ...
    def _get_output_label_from_dl_label_and_score(self, dl_label: ContentTypeLabel, score: float) -> tuple[ContentTypeLabel, OverwriteReason]: ...
    def _get_result_from_labels_and_score(self, path: Path, dl_label: ContentTypeLabel, output_label: ContentTypeLabel, score: float, overwrite_reason: OverwriteReason = ...) -> MagikaResult: ...
    def _get_result_or_features_from_path(self, path: Path) -> tuple[MagikaResult | None, ModelFeatures | None]:
        """
        Given a path, we return either a MagikaOutput or a MagikaFeatures.

        There are some files and corner cases for which we do not need to use
        deep learning to get the output; in these cases, we already return a
        MagikaOutput object.

        For some other files, we do need to use deep learning, in which case we
        return a MagikaFeatures object. Note that for now we just collect the
        features instead of already performing inference because we want to use
        batching.
        """
    def _get_result_or_features_from_seekable(self, seekable: Seekable, path: Path = ...) -> tuple[MagikaResult | None, ModelFeatures | None]:
        """
        Given a Seekable object (which is a wrapper of BinaryIO), we return
        either a MagikaOutput or a MagikaFeatures.

        There are some corner cases for which we do not need to use deep
        learning to get the output; in these cases, we return directly a
        MagikaOutput object.

        For all other cases, we do need to use deep learning, in which case we
        return a MagikaFeatures object. Note that for now we just collect the
        features instead of already performing inference because we want to use
        batching.
        """
    def _get_result_from_few_bytes(self, content: bytes, path: Path = ...) -> MagikaResult: ...
    def _get_label_from_few_bytes(self, content: bytes) -> ContentTypeLabel: ...
    def _get_raw_predictions(self, features: list[tuple[Path, ModelFeatures]]) -> npt.NDArray:
        """
        Given a list of (path, features), return a (files_num, features_size)
        matrix encoding the predictions.
        """
