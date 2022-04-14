from ..constant import PLUGIN_NAME
from ..constant import PLUGIN_STORAGE_DIR
from ..helper import expand_variables
from ..logger import Logger
from ..settings import get_merged_plugin_setting
from pathlib import Path
from typing import Dict, Optional, Set, Sequence, Union
import os
import shutil
import socket
import sublime
import subprocess


class GuesslangServer:
    server_dir = PLUGIN_STORAGE_DIR / "guesslang-server"
    server_file = PLUGIN_STORAGE_DIR / "guesslang-server/websocket.js"

    # background server process(es)
    _subprocesses: Set[subprocess.Popen] = set()

    @classmethod
    def start(cls, host: str, port: int) -> bool:
        """Starts the guesslang server and return whether it starts."""
        if not is_executable(node_path := parse_node_path()):
            sublime.error_message(f'[{PLUGIN_NAME}] Node.js binary not found or not executable: "{node_path}"')
            return False

        if is_port_in_use(port):
            Logger.log(sublime.active_window(), f"⚠ Port {port} is in use.")

        try:
            process = cls._start_process(
                (node_path, cls.server_file),
                cwd=cls.server_dir,
                extra_env={
                    "NODE_SKIP_PLATFORM_CHECK": "1",
                    "HOST": host,
                    "PORT": str(port),
                },
            )
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Fail starting guesslang server because {e}")
            return False

        if process.stdout and process.stdout.read(2) == "OK":
            cls._subprocesses.add(process)
            return True

        sublime.error_message(f"[{PLUGIN_NAME}] Fail starting guesslang server.")
        return False

    @classmethod
    def stop(cls) -> None:
        for p in cls._subprocesses:
            try:
                p.kill()
            except Exception:
                pass
        for p in cls._subprocesses:
            try:
                p.wait()
            except Exception:
                pass
        cls._subprocesses.clear()

    @classmethod
    def is_running(cls) -> bool:
        return len(cls._subprocesses) > 0

    @staticmethod
    def _start_process(
        cmd: Union[str, Path, Sequence[Union[str, Path]]],
        extra_env: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> subprocess.Popen:
        if os.name == "nt":
            # do not create a window for the process
            startupinfo = subprocess.STARTUPINFO()  # type: ignore
            startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW  # type: ignore
        else:
            startupinfo = None  # type: ignore

        env = os.environ.copy()
        env.update(extra_env or {})

        return subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            **kwargs,
        )


def parse_node_path() -> str:
    return expand_variables(get_merged_plugin_setting("guesslang.node_bin"))


def is_executable(path: Union[str, Path]) -> bool:
    return bool((os.path.isfile(path) and os.access(path, os.X_OK)) or shutil.which(path))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0
