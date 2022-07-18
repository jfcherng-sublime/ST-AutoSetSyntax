import threading
import time

import sublime_plugin

from ..constant import PLUGIN_NAME
from ..guesslang.client import GuesslangClient
from ..guesslang.server import GuesslangServer
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
        host = "localhost"
        port: int = get_merged_plugin_setting("guesslang.port")
        GuesslangServer.stop()
        if GuesslangServer.start(host, port):
            time.sleep(1)  # wait for server initialization
            G.guesslang = GuesslangClient(host, port, callback_object=GuesslangClientCallbacks())
