"""The core's in-process event stream: event types and an asyncio bus.

Components publish events; the interface and the store subscribe. Every event carries a timestamp from
the bus's injected clock, so tests drive time explicitly.
"""

import asyncio
import time
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

LinkStateName = Literal["connecting", "listening", "busy", "reconnecting", "time_limit", "stopped", "ended"]


@dataclass(frozen=True)
class LinkState:
    t: float
    state: LinkStateName
    detail: str = ""
    retry_in_s: float | None = None
    attempt: int | None = None


@dataclass(frozen=True)
class AudioBlock:
    """One SND frame's samples: 16-bit signed, little-endian, mono."""

    t: float
    seq: int
    pcm16le: bytes
    rate: float

    def samples(self) -> array:
        out = array("h")
        out.frombytes(self.pcm16le)
        return out


@dataclass(frozen=True)
class Level:
    t: float
    dbm: float


@dataclass(frozen=True)
class RawMessage:
    """A text message on the receiver socket, as sanitized for the capture."""

    t: float
    direction: Literal["→", "←"]
    msg: str
    ws: str = "SND"


Event = LinkState | AudioBlock | Level | RawMessage


class Bus:
    """Fan-out of events to every subscriber's queue, in publish order."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self.clock = clock
        self._queues: list[asyncio.Queue] = []

    def now(self) -> float:
        return self.clock()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.remove(queue)

    def publish(self, event: Event) -> None:
        for queue in self._queues:
            queue.put_nowait(event)
