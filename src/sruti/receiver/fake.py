"""The fake receiver: replays a recording (WAV + capture) as a KiwiSDR would, in memory.

It answers the link's connection with the capture's received messages and the WAV's samples as SND frames
(512 samples each, as a real receiver sends at 12 kHz), interleaved by time. Each connection can follow a
script: refuse as busy, drop after N frames, or answer with a message. Nothing listens on any port.
"""

import asyncio
import pathlib
from dataclasses import dataclass, field

from sruti.receiver import protocol
from sruti.receiver.capture import read_capture, read_wav
from sruti.receiver.transport import TransportClosed, TransportEnded

FRAME_SAMPLES = 512


@dataclass
class Behaviour:
    """What one connection does. The default streams to the end of the recording."""

    busy: bool = False  # answer MSG badp=1 and close
    drop_after_frames: int | None = None  # close after this many audio frames
    extra: list[str] = field(default_factory=list)  # text messages sent right after the greeting


class FakeReceiver:
    def __init__(self, capture: list[dict], pcm16le: bytes, rate: int = 12000, dbm: float = -95.0,
                 script: list[Behaviour] | None = None):
        self.received = [r["msg"] for r in capture if r["dir"] == "←"]
        self.pcm16le = pcm16le
        self.rate = rate
        self.dbm = dbm
        self.script = list(script or [])
        self.frames = [pcm16le[i:i + 2 * FRAME_SAMPLES] for i in range(0, len(pcm16le), 2 * FRAME_SAMPLES)]
        self.next_frame = 0  # a reconnect resumes where the stream left off
        self.sent_log: list[str] = []  # everything the link sent, across connections
        self.connections = 0
        self.open_now = 0
        self.max_open = 0

    @classmethod
    def from_recording(cls, wav: pathlib.Path, capture: pathlib.Path, **kw) -> "FakeReceiver":
        rate, pcm = read_wav(wav)
        return cls(read_capture(capture), pcm, rate=rate, **kw)

    async def connect(self, host_port: str) -> "FakeTransport":
        behaviour = self.script.pop(0) if self.script else Behaviour()
        self.connections += 1
        return FakeTransport(self, behaviour)


class FakeTransport:
    def __init__(self, receiver: FakeReceiver, behaviour: Behaviour):
        self.rx = receiver
        self.behaviour = behaviour
        self.closed = False
        self.frames_sent = 0
        self._queue = self._plan()
        receiver.open_now += 1
        receiver.max_open = max(receiver.max_open, receiver.open_now)

    def _plan(self) -> list[bytes | None]:
        """The frames to deliver, in order. None marks a close by the receiver."""
        if self.behaviour.busy:
            return [b"MSG badp=1", None]
        texts = [m.encode("utf-8") for m in self.behaviour.extra]
        if self.rx.next_frame == 0:
            texts += [m.encode("utf-8") for m in self.rx.received]
        # Text first up to audio_init (the setup answers), the rest spread evenly through the audio.
        head = next((i + 1 for i, m in enumerate(texts) if m.startswith(b"MSG audio_init")), len(texts))
        plan: list[bytes | None] = list(texts[:head])
        tail = texts[head:]
        frames = range(self.rx.next_frame, len(self.rx.frames))
        every = max(1, len(frames) // (len(tail) + 1)) if tail else 0
        for n, k in enumerate(frames):
            if tail and n and n % every == 0:
                plan.append(tail.pop(0))
            plan.append(("SND", k))  # type: ignore[arg-type]
        plan += tail
        return plan

    async def send(self, text: str) -> None:
        if self.closed:
            raise TransportClosed("closed")
        self.rx.sent_log.append(text)

    async def recv(self) -> bytes:
        await asyncio.sleep(0)  # let the link's other tasks run, as a socket read would
        if self.closed:
            raise TransportClosed("closed by the link")
        limit = self.behaviour.drop_after_frames
        if limit is not None and self.frames_sent >= limit:
            await self.close()
            raise TransportClosed("connection dropped")
        if not self._queue:
            await self.close()
            raise TransportEnded("end of recording")
        item = self._queue.pop(0)
        if item is None:
            await self.close()
            raise TransportClosed("closed by the receiver")
        if isinstance(item, tuple):
            k = item[1]
            self.rx.next_frame = k + 1
            self.frames_sent += 1
            return protocol.pack_snd(k, self.rx.dbm, self.rx.frames[k])
        return item

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.rx.open_now -= 1
