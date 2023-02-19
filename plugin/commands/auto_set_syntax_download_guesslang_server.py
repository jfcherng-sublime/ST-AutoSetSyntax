import gzip
import shutil
import tarfile
import threading
import time
import urllib.request
import zipfile
from functools import cmp_to_key
from pathlib import Path
from typing import Iterable, Optional, Union

import sublime
import sublime_plugin

from ..constant import GUESSLANG_SERVER_URL, PLUGIN_NAME
from ..guesslang.server import GuesslangServer
from ..helper import first
from ..settings import get_merged_plugin_setting
from ..shared import G

PathLike = Union[Path, str]


class AutoSetSyntaxDownloadGuesslangServerCommand(sublime_plugin.ApplicationCommand):
    # Server codes are published on https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tree/guesslang-server

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Download Guesslang Server"

    def run(self) -> None:
        self.t = threading.Thread(target=self._worker)
        self.t.start()

    def _worker(self) -> None:
        sublime.status_message("Begin downloading guesslang server...")

        if (server := G.guesslang_server) and server.is_running():
            server.stop()
            time.sleep(1)  # wait for stopping the server

        shutil.rmtree(GuesslangServer.SERVER_DIR, ignore_errors=True)

        try:
            self._prepare_bin()

            if not GuesslangServer.SERVER_FILE.is_file():
                sublime.error_message(f"[{PLUGIN_NAME}] Cannot find the server: {str(GuesslangServer.SERVER_FILE)}")

            if get_merged_plugin_setting("guesslang.enabled"):
                sublime.run_command("auto_set_syntax_restart_guesslang")

            sublime.message_dialog(f"[{PLUGIN_NAME}] Finish downloading guesslang server!")
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] {e}")

    def _prepare_bin(self) -> None:
        def sorter(a: Path, b: Path) -> int:
            return int(a.stat().st_mtime - b.stat().st_mtime)

        zip_path = GuesslangServer.SERVER_DIR / "source.zip"
        download_file(GUESSLANG_SERVER_URL, zip_path)
        decompress_file(zip_path)

        # get the folder, which is just decompressed
        folder = first(
            sorted(
                (path for path in zip_path.parent.iterdir() if path.is_dir()),
                key=cmp_to_key(sorter),
                reverse=True,
            )
        )

        if not folder:
            return

        # move the decompressed folder one level up
        guesslang_server_dir = folder.parent
        tmp_dir = guesslang_server_dir.parent / ".tmp"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        folder.replace(tmp_dir)
        shutil.rmtree(guesslang_server_dir, ignore_errors=True)
        tmp_dir.replace(guesslang_server_dir)
        # cleanup
        zip_path.unlink(missing_ok=True)


def decompress_file(tarball: PathLike, dst_dir: Optional[PathLike] = None) -> bool:
    """
    Decompress the tarball.

    :param      tarball:  The tarball
    :param      dst_dir:  The destination directory

    :returns:   Successfully decompressed the tarball or not
    """

    def tar_safe_extract(
        tar: tarfile.TarFile,
        path: PathLike = ".",
        members: Optional[Iterable[tarfile.TarInfo]] = None,
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


def download_file(url: str, save_path: PathLike) -> None:
    """
    Downloads a file.

    :param url:       The url
    :param save_path: The path of the saved file
    """

    save_path = Path(save_path)
    save_path.unlink(missing_ok=True)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(simple_urlopen(url))


def simple_urlopen(url: str, chunk_size: int = 512 * 1024) -> bytes:
    response = urllib.request.urlopen(url)
    data = b""
    while chunk := response.read(chunk_size):
        data += chunk
    if response.info().get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return data
