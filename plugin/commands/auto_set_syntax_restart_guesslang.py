import socket
import threading
import time
from typing import Iterable, Union

import sublime
import sublime_plugin

from ..constants import PLUGIN_NAME
from ..guesslang.client import GuesslangClient
from ..guesslang.server import GuesslangServer
from ..logger import Logger
from ..settings import get_merged_plugin_setting
from ..shared import G
from .auto_set_syntax import GuesslangClientCallbacks


class AutoSetSyntaxRestartGuesslangCommand(sublime_plugin.ApplicationCommand):
    def description(self) -> str:
        return f"{PLUGIN_NAME}: Restart Guesslang Client And Server"

    def is_enabled(self) -> bool:
        return bool(get_merged_plugin_setting("guesslang.enabled"))

    def run(self) -> None:
        t = threading.Thread(target=self._worker)
        t.start()

    def _worker(self) -> None:
        window = sublime.active_window()
        host = "localhost"
        port_raw = get_merged_plugin_setting("guesslang.port")
        if (port := resolve_port(port_raw)) < 0:
            Logger.log(f"⚠ Guesslang server port is unusable: {port_raw}", window=window)

        G.guesslang_server = GuesslangServer(host, port)
        if G.guesslang_server.restart():
            time.sleep(1)  # wait for server initialization
            G.guesslang = GuesslangClient(host, port, callback=GuesslangClientCallbacks())


def resolve_port(port: Union[int, str]) -> int:
    try:
        port = int(port)
    except ValueError:
        port = -1
    if 0 <= port <= 65535:
        ports: Iterable[int] = (port,)
    else:
        ports = range(30000, 65536)
    return next((p for p in ports if not is_port_in_use(p)), -1)


def is_port_in_use(port: Union[int, str]) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", int(port))) == 0
