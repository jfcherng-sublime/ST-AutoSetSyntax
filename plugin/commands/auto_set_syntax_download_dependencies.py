import gzip
import hashlib
import io
import os
import re
import shutil
import stat
import tarfile
import tempfile
import threading
import urllib.request
import uuid
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import BinaryIO
from typing import override

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..constants import PLUGIN_PY_LIBS_DIR
from ..constants import PLUGIN_PY_LIBS_URL
from ..constants import PLUGIN_PY_LIBS_ZIP_NAME

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
        # the checksum is mandatory (a missing or empty sidecar must not skip validation). Fetched
        # first, since it's tiny and the archive isn't
        sha256_url = f"{PLUGIN_PY_LIBS_URL}.sha256"
        try:
            content_hash = simple_urlopen(sha256_url).decode("utf-8").strip()
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {sha256_url} ({e})")
            return False
        if not content_hash:
            sublime.error_message(f"[{PLUGIN_NAME}] Empty SHA-256 checksum: {sha256_url}")
            return False

        url = PLUGIN_PY_LIBS_URL
        try:
            content_bytes = simple_urlopen(url, timeout=1800)
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {url} ({e})")
            return False

        if hashlib.sha256(content_bytes).hexdigest().casefold() != content_hash.casefold():
            sublime.error_message(f"[{PLUGIN_NAME}] SHA-256 checksum mismatches: {PLUGIN_PY_LIBS_URL}")
            return False

        # extract into a scratch parent dir first so a corrupt/incomplete archive never destroys a
        # working install; the archive's own top-level entry is named like `PLUGIN_PY_LIBS_DIR`.
        # A sibling of it, so installing is a rename on the same filesystem, not a copy
        PLUGIN_PY_LIBS_DIR.parent.mkdir(parents=True, exist_ok=True)
        tmp_parent = Path(
            tempfile.mkdtemp(prefix=f"{PLUGIN_PY_LIBS_DIR.name}{_TMP_DIR_INFIX}", dir=PLUGIN_PY_LIBS_DIR.parent)
        )
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

            return _swap_in(extracted_dir)
        finally:
            rmtree_ex(tmp_parent, ignore_errors=True)


_TMP_DIR_INFIX = ".tmp-"
_OLD_DIR_INFIX = ".old-"


def _swap_in(new_dir: Path) -> bool:
    """
    Replace `PLUGIN_PY_LIBS_DIR` with `new_dir`. Returns whether it succeeded.

    Rename the old install aside rather than delete it: on Windows, a loaded DLL (e.g. Magika's
    onnxruntime) can't be deleted, so deleting got halfway -- leaving a broken install that the
    new one was then moved *into*, as a subdirectory. A directory holding a loaded DLL can still
    be renamed, though, and a rename that fails changes nothing.
    """
    backup_dir: Path | None = None
    if PLUGIN_PY_LIBS_DIR.exists():
        backup_dir = PLUGIN_PY_LIBS_DIR.with_name(f"{PLUGIN_PY_LIBS_DIR.name}{_OLD_DIR_INFIX}{uuid.uuid4().hex[:8]}")
        try:
            PLUGIN_PY_LIBS_DIR.rename(backup_dir)
        except OSError as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Cannot move the old dependencies aside: {e}")
            return False

    try:
        new_dir.rename(PLUGIN_PY_LIBS_DIR)
    except OSError as e:
        if backup_dir:
            backup_dir.rename(PLUGIN_PY_LIBS_DIR)
        sublime.error_message(f"[{PLUGIN_NAME}] Cannot install the new dependencies: {e}")
        return False

    if backup_dir:
        # its DLLs may still be loaded; whatever is left is removed on the next start
        rmtree_ex(backup_dir, ignore_errors=True)
    return True


def rmtree_ex(path: str | Path, ignore_errors: bool = False) -> None:
    """
    Remove the given recursively.

    :note: we use shutil rmtree but adjust its behaviour to see whether files that
        couldn't be deleted are read-only. Windows will not remove them in that case

    @see https://github.com/gitpython-developers/GitPython/blob/ea43defd777a9c0751fc44a9c6a622fc2dbd18a0/git/util.py#L101-L118
    """
    if os.name == "nt" and (path := Path(path)).is_absolute():
        path = Rf"\\?\{path}"  # use UNC path to resolve Windows long path issue

    def onexc(func: Callable, path: str | Path, exec_info: Any) -> None:
        try:
            os.chmod(path, stat.S_IWUSR)
            func(path)  # will scream if still not possible to delete.
        except Exception:
            if not ignore_errors:
                raise

    return shutil.rmtree(path, False, onexc=onexc)


def remove_stale_dependency_dirs() -> None:
    """Remove the old installs and scratch dirs a previous download couldn't, e.g. for a loaded DLL."""
    if not (parent := PLUGIN_PY_LIBS_DIR.parent).is_dir():
        return
    for infix in (_TMP_DIR_INFIX, _OLD_DIR_INFIX):
        for path in parent.glob(f"{PLUGIN_PY_LIBS_DIR.name}{infix}*"):
            rmtree_ex(path, ignore_errors=True)


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


def simple_urlopen(url: str, *, chunk_size: int = 512 * 1024, timeout: float = 30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        buffer = io.BytesIO()
        shutil.copyfileobj(resp, buffer, length=chunk_size)
        data = buffer.getvalue()
        if resp.info().get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data
