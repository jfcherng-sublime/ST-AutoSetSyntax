from __future__ import annotations

import gzip
import hashlib
import tarfile
import threading
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Union

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME, PLUGIN_PY_LIBS_DIR, PLUGIN_PY_LIBS_URL, PLUGIN_PY_LIBS_ZIP_NAME
from ..utils import rmtree_ex

PathLike = Union[Path, str]


class AutoSetSyntaxDownloadDependenciesCommand(sublime_plugin.ApplicationCommand):
    # Dependencies are published on https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tree/dependencies

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
        zip_path = PLUGIN_PY_LIBS_DIR.parent / PLUGIN_PY_LIBS_ZIP_NAME
        rmtree_ex(PLUGIN_PY_LIBS_DIR, ignore_errors=True)

        try:
            content_bytes = simple_urlopen(PLUGIN_PY_LIBS_URL)
            content_md5 = simple_urlopen(f"{PLUGIN_PY_LIBS_URL}.md5").decode("utf-8").strip()
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Error while fetching: {PLUGIN_PY_LIBS_URL} ({e})")
            return

        if md5sum(content_bytes).casefold() != content_md5.casefold():
            sublime.error_message(f"[{PLUGIN_NAME}] MD5 checksum mismatches: {PLUGIN_PY_LIBS_ZIP_NAME}")
            return

        save_content(content_md5, f"{zip_path}.md5")
        save_content(content_bytes, zip_path)
        decompress_file(zip_path)
        zip_path.unlink(missing_ok=True)


def decompress_file(tarball: PathLike, dst_dir: PathLike | None = None) -> bool:
    """
    Decompress the tarball.

    :param      tarball:  The tarball
    :param      dst_dir:  The destination directory

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

    tarball = Path(tarball)
    dst_dir = Path(dst_dir) if dst_dir else tarball.parent
    filename = tarball.name

    try:
        if filename.endswith(".tar.gz"):
            with tarfile.open(tarball, "r:gz") as f_1:
                tar_safe_extract(f_1, dst_dir)
            return True

        if filename.endswith(".tar"):
            with tarfile.open(tarball, "r:") as f_2:
                tar_safe_extract(f_2, dst_dir)
            return True

        if filename.endswith(".zip"):
            with zipfile.ZipFile(tarball) as f_3:
                f_3.extractall(dst_dir)
            return True
    except Exception:
        pass
    return False


def simple_urlopen(url: str, *, chunk_size: int = 512 * 1024) -> bytes:
    response = urllib.request.urlopen(url)
    data = b""
    while chunk := response.read(chunk_size):
        data += chunk
    if response.info().get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return data


def save_content(content: str | bytes, path: PathLike, *, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        path.write_text(content, encoding=encoding)
    else:
        path.write_bytes(content)


def md5sum(target: bytes | str | Path, *, encoding: str = "utf-8") -> str:
    """Calculates the lowercase MD5 hash of the string, bytes or file."""
    if isinstance(target, str):
        target = target.encode(encoding)
    elif isinstance(target, Path):
        target = target.read_bytes()

    hasher = hashlib.md5()
    hasher.update(target)
    return hasher.hexdigest()
