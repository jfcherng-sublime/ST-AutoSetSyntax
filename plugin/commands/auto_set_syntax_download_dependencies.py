from __future__ import annotations

import gzip
import hashlib
import io
import re
import tarfile
import threading
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import IO, Union

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, PLUGIN_PY_LIBS_DIR, PLUGIN_PY_LIBS_URL, PLUGIN_PY_LIBS_ZIP_NAME
from ..utils import rmtree_ex

PathLike = Union[Path, str]


class AutoSetSyntaxDownloadDependenciesCommand(sublime_plugin.ApplicationCommand):
    # Dependencies are published on https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tree/dependencies-v1-models

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Download Dependencies"

    def run(self) -> None:
        self.t = threading.Thread(target=self._worker)
        self.t.start()

    @classmethod
    def _worker(cls) -> None:
        sublime.message_dialog(f"[{PLUGIN_NAME}] Start downloading dependencies...")

        cls._prepare_dependencies()

        if not (magika_dir := PLUGIN_PY_LIBS_DIR / "magika").is_dir():
            sublime.error_message(f"[{PLUGIN_NAME}] Cannot find magika: {str(magika_dir)}")

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


def decompress_buffer(buffer: IO[bytes], *, filename: str, dst_dir: PathLike) -> bool:
    """
    Decompress the tarball in the bytes IO object.

    :param      buffer:    The buffer bytes IO object
    :param      filename:  The filename used to determine the decompression method
    :param      dst_dir:   The destination dir

    :returns:   Successfully decompressed the tarball or not
    """

    def tar_safe_extract(
        tar: tarfile.TarFile,
        path: PathLike = ".",
        members: Iterable[tarfile.TarInfo] | None = None,
        *,
        numeric_owner: bool = False,
    ) -> None:
        path = Path(path).resolve()
        for member in tar.getmembers():
            member_path = (path / member.name).resolve()
            if path not in member_path.parents:
                raise Exception("Attempted Path Traversal in Tar File")

        tar.extractall(path, members, numeric_owner=numeric_owner)

    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if m := re.search(r"\.tar(?:\.(bz2|gz|xz))?$", filename):
        sub_ext = m.group(1) or ""
        with tarfile.open(fileobj=buffer, mode=f"r:{sub_ext}") as tar_f:
            tar_safe_extract(tar_f, dst_dir)
        return True

    if filename.endswith(".zip"):
        with zipfile.ZipFile(buffer) as zip_f:
            zip_f.extractall(dst_dir)
        return True

    return False


def decompress_file(tarball: PathLike, dst_dir: PathLike | None = None) -> bool:
    """
    Decompress the tarball file.

    :param      tarball:  The tarball
    :param      dst_dir:  The destination directory

    :returns:   Successfully decompressed the tarball or not
    """
    tarball = Path(tarball)
    dst_dir = Path(dst_dir) if dst_dir else tarball.parent

    with tarball.open("rb") as f:
        return decompress_buffer(f, filename=tarball.name, dst_dir=dst_dir)


def simple_urlopen(url: str, *, chunk_size: int = 512 * 1024) -> bytes:
    with urllib.request.urlopen(url) as resp:
        data = b""
        while chunk := resp.read(chunk_size):
            data += chunk
        if resp.info().get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data


def save_content(content: str | bytes, path: PathLike, *, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        path.write_text(content, encoding=encoding)
    else:
        path.write_bytes(content)


def sha256sum(target: bytes | str | Path, *, encoding: str = "utf-8") -> str:
    """Calculates the lowercase SHA-256 hash of the string, bytes or file."""
    if isinstance(target, str):
        target = target.encode(encoding)
    elif isinstance(target, Path):
        target = target.read_bytes()

    return hashlib.sha256(target).hexdigest()
