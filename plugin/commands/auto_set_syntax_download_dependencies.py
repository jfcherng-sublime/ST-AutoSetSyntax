import gzip
import hashlib
import io
import re
import shutil
import tarfile
import tempfile
import threading
import urllib.error
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

        if not cls._prepare_dependencies():
            return

        if not (magika_dir := PLUGIN_PY_LIBS_DIR / "magika").is_dir():
            sublime.error_message(f"[{PLUGIN_NAME}] Cannot find magika: {magika_dir!s}")
            return

        sublime.message_dialog(f"[{PLUGIN_NAME}] Finish downloading dependencies!")

    @staticmethod
    def _prepare_dependencies() -> bool:
        """Download, verify and install dependencies. Returns whether it succeeded."""
        url = PLUGIN_PY_LIBS_URL
        try:
            content_bytes = simple_urlopen(url)
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {url} ({e})")
            return False

        sha256_url = f"{PLUGIN_PY_LIBS_URL}.sha256"
        try:
            content_hash = simple_urlopen(sha256_url).decode("utf-8").strip()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {sha256_url} ({e})")
                return False
            print(f"[{PLUGIN_NAME}] Error while fetching: {sha256_url} ({e}; skip checksum validation)")
            content_hash = ""
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {sha256_url} ({e})")
            return False

        if content_hash and sha256sum(content_bytes).casefold() != content_hash.casefold():
            sublime.error_message(f"[{PLUGIN_NAME}] SHA-256 checksum mismatches: {PLUGIN_PY_LIBS_URL}")
            return False

        # extract into a scratch parent dir first so a corrupt/incomplete archive never destroys a
        # working install; the archive's own top-level entry is named like `PLUGIN_PY_LIBS_DIR`
        tmp_parent = Path(tempfile.mkdtemp(prefix=f"{PLUGIN_NAME}-deps-"))
        try:
            try:
                ok = decompress_buffer(io.BytesIO(content_bytes), filename=PLUGIN_PY_LIBS_ZIP_NAME, dst_dir=tmp_parent)
                if not ok:
                    sublime.error_message(f"[{PLUGIN_NAME}] Unrecognized archive format: {PLUGIN_PY_LIBS_ZIP_NAME}")
                    return False
            except Exception as e:
                sublime.error_message(f"[{PLUGIN_NAME}] Error while extracting dependencies: {e}")
                return False

            extracted_dir = tmp_parent / PLUGIN_PY_LIBS_DIR.name
            if not extracted_dir.is_dir():
                sublime.error_message(
                    f"[{PLUGIN_NAME}] Archive didn't contain the expected {PLUGIN_PY_LIBS_DIR.name!r} directory"
                )
                return False

            rmtree_ex(PLUGIN_PY_LIBS_DIR, ignore_errors=True)
            shutil.move(str(extracted_dir), str(PLUGIN_PY_LIBS_DIR))
        finally:
            rmtree_ex(tmp_parent, ignore_errors=True)

        return True


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
