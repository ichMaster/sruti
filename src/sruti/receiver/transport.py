"""The link's transport: a small interface, with the real one on `websockets`.

The link only ever sees `Transport`, so the fake receiver can stand in for a real KiwiSDR in memory —
no socket, nothing listening, not even on loopback.
"""

import asyncio
import json
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Protocol

import websockets


class TransportClosed(Exception):
    """The connection ended; the link reconnects."""


class TransportEnded(TransportClosed):
    """The source has nothing more to send (a replay finished); the link stops instead of reconnecting."""


class Transport(Protocol):
    async def send(self, text: str) -> None: ...
    async def recv(self) -> bytes: ...
    async def close(self) -> None: ...


Connector = Callable[[str], Awaitable[Transport]]

MAX_MESSAGE = 1 << 20  # the largest seen is ~47 KB (load_dxcfg); audio frames are ~1 KB


def fetch_timestamp(host_port: str, timeout: float = 10.0) -> int:
    """The connection timestamp the receiver issues at /VER, as its browser page asks for it."""
    url = f"http://{host_port}/VER"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return int(json.load(resp)["ts"])


class WebSocketTransport:
    def __init__(self, connection):
        self._ws = connection

    async def send(self, text: str) -> None:
        try:
            await self._ws.send(text)
        except websockets.ConnectionClosed as exc:
            raise TransportClosed(str(exc)) from None

    async def recv(self) -> bytes:
        try:
            data = await self._ws.recv()
        except websockets.ConnectionClosed as exc:
            raise TransportClosed(str(exc)) from None
        return data.encode("utf-8") if isinstance(data, str) else data

    async def close(self) -> None:
        await self._ws.close()


async def connect_kiwisdr(host_port: str) -> Transport:
    """Connect the way the receiver's browser page does: /VER, then /ws/no_wf/<ts>/SND."""
    try:
        ts = await asyncio.to_thread(fetch_timestamp, host_port)
        connection = await websockets.connect(
            f"ws://{host_port}/ws/no_wf/{ts}/SND", open_timeout=15, ping_interval=None, compression=None,
            max_size=MAX_MESSAGE)
    except (OSError, TimeoutError, ValueError, KeyError, websockets.InvalidHandshake) as exc:
        raise TransportClosed(f"could not connect to {host_port}: {type(exc).__name__}: {exc}") from None
    return WebSocketTransport(connection)
