from ..constant import PLUGIN_NAME
from ..constant import PLUGIN_STORAGE_DIR
from ..helper import expand_variables
from ..logger import Logger
from ..settings import get_merged_plugin_setting
from typing import Dict, List, Optional, Sequence, Union
import os
import shutil
import socket
import sublime
import subprocess

# background server process(es)
_subprocesses: List[subprocess.Popen] = []


class GuesslangServer:
    server_dir = PLUGIN_STORAGE_DIR / "guesslang-server"
    server_file = PLUGIN_STORAGE_DIR / "guesslang-server/websocket.js"

    @classmethod
    def start(cls, host: str, port: int) -> bool:
        """Starts the guesslang server and return whether it starts."""
        node_path = parse_node_path()
        if not is_executable(node_path):
            sublime.error_message(
                f'[{PLUGIN_NAME}] Node.js binary not found or not executable. Exepected path: "{node_path}"'
            )
            return False

        if is_port_in_use(port):
            Logger.log(sublime.active_window(), f"⚠ Port {port} is in use.")
        else:
            try:
                process = start_server_process(
                    (node_path, str(cls.server_file)),
                    cwd=str(cls.server_dir),
                    extra_env={
                        "NODE_SKIP_PLATFORM_CHECK": "1",
                        "HOST": host,
                        "PORT": str(port),
                    },
                )
                _, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                return True
            except Exception as e:
                sublime.error_message(f"[{PLUGIN_NAME}] Fail starting guesslang server.\n\n{e}")
                return False

            sublime.error_message(f"[{PLUGIN_NAME}] Fail starting guesslang server.\n\n{stderr}")

            try:
                _subprocesses.remove(process)
            except ValueError:
                pass
            return False

        return True

    @classmethod
    def stop(cls) -> None:
        for p in _subprocesses:
            try:
                p.kill()
            except Exception:
                pass
        for p in _subprocesses:
            try:
                p.wait()
            except Exception:
                pass
        _subprocesses.clear()

    @classmethod
    def is_running(cls) -> bool:
        return len(_subprocesses) > 0


def parse_node_path() -> str:
    return expand_variables(get_merged_plugin_setting(sublime.active_window(), "guesslang.node_bin"))


def is_executable(path: str) -> bool:
    return bool((os.path.isfile(path) and os.access(path, os.X_OK)) or shutil.which(path))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def start_server_process(
    cmd: Union[str, Sequence[str]],
    cwd: str = "",
    shell: bool = False,
    extra_env: Optional[Dict[str, str]] = None,
) -> subprocess.Popen:
    if os.name == "nt":
        # do not create a window for the process
        startupinfo = subprocess.STARTUPINFO()  # type: ignore
        startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW  # type: ignore
    else:
        startupinfo = None  # type: ignore

    env = os.environ.copy()
    env.update(extra_env or {})

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        startupinfo=startupinfo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        shell=shell,
        env=env,
    )
    _subprocesses.append(process)

    return process
