from __future__ import annotations

import threading
from typing import Protocol

import sublime

from ..libs import websocket
from ..snapshot import ViewSnapshot
from ..types import ListenerEvent


class TransportCallbacks(Protocol):
    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Called when connected to the websocket."""

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Called when received a message from the websocket."""

    def on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        """Called when there is an exception occurred in the websocket."""

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Called when disconnected from the websocket."""


class NullTransportCallbacks:
    on_open = None
    on_message = None
    on_error = None
    on_close = None


class GuesslangClient:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        callback: TransportCallbacks | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.callback = callback or NullTransportCallbacks()
        # internals
        self._ws: websocket.WebSocketApp | None = None

    def __del__(self) -> None:
        if self._ws:
            self._ws.close()

    def connect(self) -> None:
        def _worker(client: GuesslangClient) -> None:
            client._ws = websocket.WebSocketApp(
                f"ws://{client.host}:{client.port}",
                on_open=client.callback.on_open,
                on_message=client.callback.on_message,
                on_error=client.callback.on_error,
                on_close=client.callback.on_close,
            )
            client._ws.run_forever()

        if not self.is_connected():
            # websocket.enableTrace(True)
            self.thread = threading.Thread(target=_worker, args=(self,))
            self.thread.start()

    def is_connected(self) -> bool:
        return bool(self._ws and self._ws.sock)

    def request_guess_snapshot(
        self,
        view_snapshot: ViewSnapshot,
        *,
        event: ListenerEvent | None = None,
    ) -> None:
        if self.is_connected():
            assert self._ws
            self._ws.send(
                sublime.encode_value(
                    {
                        "id": view_snapshot.id,
                        "content": view_snapshot.content,
                        "event_name": event.value if event else None,
                    }
                )
            )
