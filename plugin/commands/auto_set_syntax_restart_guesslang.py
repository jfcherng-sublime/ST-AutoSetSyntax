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
from ..utils import first_true
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
        port_raw = get_merged_plugin_setting("guesslang.port")
        if (port := _resolve_port(port_raw)) < 0:
            Logger.log(f"❌ Guesslang server port is unusable: {port_raw}", window=window)
            return

        host = "localhost"
        G.guesslang_client = G.guesslang_client or GuesslangClient(host, port, callback=GuesslangClientCallbacks())
        G.guesslang_server = G.guesslang_server or GuesslangServer(host, port)
        if G.guesslang_server.restart():
            time.sleep(1)  # wait for server initialization
            G.guesslang_client.connect()


def _resolve_port(port: Union[int, str]) -> int:
    try:
        port = int(port)
    except ValueError:
        port = -1
    if 0 <= port <= 65535:
        ports: Iterable[int] = (port,)
    else:
        ports = range(30000, 65536)
    return first_true(ports, -1, pred=_is_port_available)


def _is_port_available(port: Union[int, str]) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", int(port))) != 0
