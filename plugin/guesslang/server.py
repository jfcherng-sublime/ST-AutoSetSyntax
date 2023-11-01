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
    SERVER_FILE: Final[Path] = SERVER_DIR / "websocket.js"

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._proc: subprocess.Popen | None = None
        """The server process."""

    def start(self) -> bool:
        """Starts the guesslang server and return whether it starts."""
        if self._proc:
            Logger.log("⚠️ Server is already running.")
            return True
        if not (node_info := parse_node_path_args()):
            Logger.log("❌ Node.js binary is not found or not executable.")
            return False
        node_path, node_args = node_info
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
            Logger.log(f"❌ Failed starting guesslang server: {e}")
            return False

        if process.stdout and process.stdout.read(2) == "OK":
            self._proc = process
            return True

        Logger.log("❌ Failed starting guesslang server.")
        return False

    def stop(self) -> None:
        if not self._proc:
            return
        try:
            self._proc.kill()
        except Exception:
            pass
        try:
            self._proc.wait()
        except Exception:
            pass
        self._proc = None

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def is_running(self) -> bool:
        return self._proc is not None

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

        if isinstance(cmd, (str, Path)):
            kwargs["shell"] = True

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


def parse_node_path_args() -> tuple[str, list[str]] | None:
    for node, args in (
        (
            get_merged_plugin_setting("guesslang.node_bin"),
            get_merged_plugin_setting("guesslang.node_bin_args"),
        ),
        ("${lsp_utils_node_bin}", []),
        ("electron", []),
        ("node", []),
        ("code", ["--ms-enable-electron-run-as-node"]),  # VSCode
        ("codium", []),  # VSCodium (non-Windows)
        ("VSCodium", []),  # VSCodium (Windows)
    ):
        if (node := shutil.which(expand_variables(node)) or "") and is_executable(node):
            return (node, args)
    return None


def is_executable(path: str | Path) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)
