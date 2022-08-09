import threading
from typing import Optional, Protocol

import sublime

from ..libs import websocket
from ..types import ListenerEvent, TD_ViewSnapshot
from .types import DetectorModel


class TransportCallbacks(Protocol):
    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Called when connected to the websocket."""
        pass

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Called when received a message from the websocket."""
        pass

    def on_error(self, ws: websocket.WebSocketApp, error: str) -> None:
        """Called when there is an exception occurred in the websocket."""
        pass

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Called when disconnected from the websocket."""
        pass


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
        callback_object: Optional[TransportCallbacks] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.callback_object = callback_object or NullTransportCallbacks()

        self.ws: Optional[websocket.WebSocketApp] = None
        self._start_client_thread()

    def __del__(self) -> None:
        if self.ws:
            self.ws.close()

    def _start_client_thread(self) -> None:
        def _worker(client: GuesslangClient) -> None:
            client.ws = websocket.WebSocketApp(
                f"ws://{client.host}:{client.port}",
                on_open=client.callback_object.on_open,
                on_message=client.callback_object.on_message,
                on_error=client.callback_object.on_error,
                on_close=client.callback_object.on_close,
            )
            client.ws.run_forever()

        # websocket.enableTrace(True)
        self.thread = threading.Thread(target=_worker, args=(self,))
        self.thread.start()

    @staticmethod
    def is_connected(ws: websocket.WebSocketApp) -> bool:
        return ws.sock is not None

    def request_guess_snapshot(
        self,
        view_info: TD_ViewSnapshot,
        *,
        model: DetectorModel = DetectorModel.DEFAULT,
        event: Optional[ListenerEvent] = None,
    ) -> None:
        if self.ws and self.is_connected(self.ws):
            self.ws.send(
                sublime.encode_value(
                    {
                        "id": view_info["id"],
                        "model": model.value,
                        "content": view_info["content"],
                        "event_name": event.value if event else None,
                    }
                )
            )
