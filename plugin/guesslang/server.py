from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final, Sequence

from ..constants import PLUGIN_STORAGE_DIR
from ..logger import Logger
from ..settings import get_merged_plugin_setting
from ..utils import expand_variables


class GuesslangServer:
    SERVER_DIR: Final[Path] = PLUGIN_STORAGE_DIR / "guesslang-server"
    SERVER_FILE: Final[Path] = PLUGIN_STORAGE_DIR / "guesslang-server/websocket.js"

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        # background server process(es)
        self._subprocesses: set[subprocess.Popen] = set()

    def start(self) -> bool:
        """Starts the guesslang server and return whether it starts."""
        node_path, node_args = parse_node_path_args()
        if not node_path:
            Logger.log("❌ Node.js binary is not found or not executable")
            return False
        Logger.log(f"✔ Use Node.js binary ({node_path}) and args ({node_args})")

        try:
            process = self._start_process(
                (node_path, *node_args, self.SERVER_FILE),
                cwd=self.SERVER_DIR,
                extra_env={
                    "ELECTRON_RUN_AS_NODE": "1",
                    "NODE_SKIP_PLATFORM_CHECK": "1",
                    "HOST": self.host,
                    "PORT": str(self.port),
                },
            )
        except Exception as e:
            Logger.log(f"❌ Failed starting guesslang server because {e}")
            return False

        if process.stdout and process.stdout.read(2) == "OK":
            self._subprocesses.add(process)
            return True

        Logger.log("❌ Failed starting guesslang server.")
        return False

    def stop(self) -> None:
        for p in self._subprocesses:
            try:
                p.kill()
            except Exception:
                pass
        for p in self._subprocesses:
            try:
                p.wait()
            except Exception:
                pass
        self._subprocesses.clear()

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def is_running(self) -> bool:
        return len(self._subprocesses) > 0

    @staticmethod
    def _start_process(
        cmd: str | Path | Sequence[str | Path],
        extra_env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.Popen:
        if os.name == "nt":
            # do not create a window for the process
            startupinfo = subprocess.STARTUPINFO()  # type: ignore
            startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW  # type: ignore
        else:
            startupinfo = None  # type: ignore

        return subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, **(extra_env or {})),
            **kwargs,
        )


def parse_node_path_args() -> tuple[str | None, list[str]]:
    for node, args in (
        (
            get_merged_plugin_setting("guesslang.node_bin"),
            get_merged_plugin_setting("guesslang.node_bin_args"),
        ),
        (R"${lsp_utils_node_bin}", []),
        (shutil.which("electron"), []),
        (shutil.which("node"), []),
        (shutil.which("code"), ["--ms-enable-electron-run-as-node"]),  # VSCode
        (shutil.which("codium"), []),  # VSCodium (non-Windows)
        (shutil.which("VSCodium"), []),  # VSCodium (Windows)
    ):
        if (node := expand_variables(node)) and is_executable(node):
            return (node, args)
    return (None, [])


def is_executable(path: str | Path) -> bool:
    return bool((os.path.isfile(path) and os.access(path, os.X_OK)))
