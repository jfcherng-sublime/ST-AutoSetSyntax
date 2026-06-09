import gzip
import hashlib
import io
import re
import shutil
import tarfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import BinaryIO
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..constants import PLUGIN_PY_LIBS_DIR
from ..constants import PLUGIN_PY_LIBS_URL
from ..constants import PLUGIN_PY_LIBS_ZIP_NAME
from ..utils import rmtree_ex

type PathLike = Path | str


class AutoSetSyntaxDownloadDependenciesCommand(sublime_plugin.ApplicationCommand):
    # Dependencies are published on https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tree/dependencies-v3-models

    @override
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Download Dependencies"

    @override
    def run(self) -> None:
        self.t = threading.Thread(target=self._worker)
        self.t.start()

    @classmethod
    def _worker(cls) -> None:
        sublime.message_dialog(f"[{PLUGIN_NAME}] Start downloading dependencies...")

        cls._prepare_dependencies()

        if not (magika_dir := PLUGIN_PY_LIBS_DIR / "magika").is_dir():
            sublime.error_message(f"[{PLUGIN_NAME}] Cannot find magika: {magika_dir!s}")

        sublime.message_dialog(f"[{PLUGIN_NAME}] Finish downloading dependencies!")

    @staticmethod
    def _prepare_dependencies() -> None:
        url = PLUGIN_PY_LIBS_URL
        try:
            content_bytes = simple_urlopen(url)
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {url} ({e})")
            return

        url = f"{PLUGIN_PY_LIBS_URL}.sha256"
        try:
            content_hash = simple_urlopen(url).decode("utf-8").strip()
        except Exception as e:
            print(f"[{PLUGIN_NAME}] Error while fetching: {url} ({e}; skip checksum validation)")
            content_hash = ""

        if content_hash and sha256sum(content_bytes).casefold() != content_hash.casefold():
            sublime.error_message(f"[{PLUGIN_NAME}] SHA-256 checksum mismatches: {PLUGIN_PY_LIBS_URL}")
            return

        rmtree_ex(PLUGIN_PY_LIBS_DIR, ignore_errors=True)
        decompress_buffer(
            io.BytesIO(content_bytes),
            filename=PLUGIN_PY_LIBS_ZIP_NAME,
            dst_dir=PLUGIN_PY_LIBS_DIR.parent,
        )


def decompress_buffer(buffer: BinaryIO, *, filename: str, dst_dir: PathLike) -> bool:
    """
    Decompress the tarball in the bytes IO object.

    :param      buffer:    The buffer bytes IO object
    :param      filename:  The filename used to determine the decompression method
    :param      dst_dir:   The destination dir

    :returns:   Successfully decompressed the tarball or not
    """
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if re.search(r"\.tar(?:\.(bz2|gz|xz))?$", filename):
        with tarfile.open(fileobj=buffer, mode="r:*") as tar_f:
            tar_f.extractall(dst_dir, filter="data")
        return True

    if filename.endswith(".zip"):
        with zipfile.ZipFile(buffer) as zip_f:
            zip_f.extractall(dst_dir)
        return True

    return False


def simple_urlopen(url: str, *, chunk_size: int = 512 * 1024) -> bytes:
    with urllib.request.urlopen(url) as resp:
        buffer = io.BytesIO()
        shutil.copyfileobj(resp, buffer, length=chunk_size)
        data = buffer.getvalue()
        if resp.info().get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data


def sha256sum(target: bytes | str | Path, *, encoding: str = "utf-8") -> str:
    """Calculates the lowercase SHA-256 hash of the string, bytes or file."""
    match target:
        case Path():
            with target.open("rb") as f:
                return hashlib.file_digest(f, "sha256").hexdigest()
        case str():
            target = target.encode(encoding)
    return hashlib.sha256(target).hexdigest()
