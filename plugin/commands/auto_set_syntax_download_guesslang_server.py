from __future__ import annotations

# __future__ must be the first import
from ..constant import GITHUB_TAGS_API
from ..constant import PLUGIN_NAME
from ..guesslang.server import GuesslangServer
from ..types_github import GithubApiTags
from functools import cmp_to_key
from pathlib import Path
from typing import Optional, Union
import gzip
import os
import shutil
import sublime
import sublime_plugin
import tarfile
import threading
import urllib.request
import zipfile


class AutoSetSyntaxDownloadGuesslangServerCommand(sublime_plugin.ApplicationCommand):
    # Server codes are published on https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tree/guesslang-server

    def description(self) -> str:
        return f"{PLUGIN_NAME}: Download Guesslang Server"

    def run(self) -> None:
        self.t = threading.Thread(target=self._worker)
        self.t.start()

    def _worker(self) -> None:
        sublime.status_message("Begin downloading guesslang server...")

        if not (url := find_latest_download_url()):
            sublime.error_message(f"[{PLUGIN_NAME}] Cannot find a download URL for guesslang server.")
            return

        is_running = GuesslangServer.is_running()

        # otherwise, the server directory is locked
        GuesslangServer.stop()
        shutil.rmtree(GuesslangServer.server_dir, ignore_errors=True)

        try:
            zip_path = GuesslangServer.server_dir / "source.zip"
            download_file(url, zip_path)
            decompress_file(str(zip_path))
            self._chore(zip_path)

            if is_running:
                sublime.run_command("auto_set_syntax_restart_guesslang")

            sublime.message_dialog(f"[{PLUGIN_NAME}] Finish downloading guesslang server!")
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] {e}")

    def _chore(self, zip_path: Path) -> None:
        def _sorter(a: Path, b: Path) -> int:
            return int(a.stat().st_mtime - b.stat().st_mtime)

        # get the folder, which is just decompressed
        folder = next(
            iter(
                sorted(
                    (path for path in zip_path.parent.iterdir() if path.is_dir()),
                    key=cmp_to_key(_sorter),
                    reverse=True,
                )
            ),
            None,
        )

        if not folder:
            return

        # move the decompressed folder one level up
        guesslang_server_dir = folder.parent
        tmp_dir = guesslang_server_dir.parent / "_"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        folder.replace(tmp_dir)
        shutil.rmtree(guesslang_server_dir, ignore_errors=True)
        tmp_dir.replace(guesslang_server_dir)
        zip_path.unlink(missing_ok=True)


def simple_urlopen(url: str) -> bytes:
    response = urllib.request.urlopen(url)
    data = response.read()
    if response.info().get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return data


def find_latest_download_url() -> Optional[str]:
    data = simple_urlopen(GITHUB_TAGS_API)
    tags: GithubApiTags = sublime.decode_value(data.decode("utf-8"))
    # these tags are ordered by created time DESC
    for tag in tags:
        if tag["name"].startswith("server-"):
            return tag["zipball_url"]
    return None


def decompress_file(tarball: str, dst_dir: Optional[str] = None) -> None:
    """
    Decompress the tarball.

    :param      tarball:  The tarball
    :param      dst_dir:  The destination directory
    """

    if not dst_dir:
        dst_dir = os.path.dirname(tarball)

    if tarball.endswith(".tar.gz"):
        with tarfile.open(tarball, "r:gz") as f_1:
            f_1.extractall(dst_dir)
        return

    if tarball.endswith(".tar"):
        with tarfile.open(tarball, "r:") as f_2:
            f_2.extractall(dst_dir)
        return

    if tarball.endswith(".zip"):
        with zipfile.ZipFile(tarball) as f_3:
            f_3.extractall(dst_dir)
        return


def download_file(url: str, save_path: Union[Path, str]) -> None:
    """
    Downloads a file.

    :param url:       The url
    :param save_path: The path of the saved file
    """

    save_path = Path(save_path)
    save_path.unlink(missing_ok=True)
    save_path.parent.mkdir(exist_ok=True)
    with save_path.open("wb") as f:
        f.write(simple_urlopen(url))
