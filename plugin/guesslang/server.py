import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Final, Optional, Sequence, Set, Union

import sublime

from ..constants import PLUGIN_NAME, PLUGIN_STORAGE_DIR
from ..helper import expand_variables
from ..settings import get_merged_plugin_setting


class GuesslangServer:
    SERVER_DIR: Final[Path] = PLUGIN_STORAGE_DIR / "guesslang-server"
    SERVER_FILE: Final[Path] = PLUGIN_STORAGE_DIR / "guesslang-server/websocket.js"

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        # background server process(es)
        self._subprocesses: Set[subprocess.Popen] = set()

    def start(self) -> bool:
        """Starts the guesslang server and return whether it starts."""
        if not is_executable(node_path := parse_node_path()):
            sublime.error_message(f'[{PLUGIN_NAME}] Node.js binary not found or not executable: "{node_path}"')
            return False

        try:
            process = self._start_process(
                (node_path, self.SERVER_FILE),
                cwd=self.SERVER_DIR,
                extra_env={
                    "NODE_SKIP_PLATFORM_CHECK": "1",
                    "HOST": self.host,
                    "PORT": str(self.port),
                },
            )
        except Exception as e:
            sublime.error_message(f"[{PLUGIN_NAME}] Failed starting guesslang server because {e}")
            return False

        if process.stdout and process.stdout.read(2) == "OK":
            self._subprocesses.add(process)
            return True

        sublime.error_message(f"[{PLUGIN_NAME}] Failed starting guesslang server.")
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
