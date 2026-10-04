"""The receiver link: one CW audio channel on a KiwiSDR, turned into core events.

Connects, tunes, keeps the channel alive and publishes `AudioBlock`, `Level`, `RawMessage` and `LinkState`
events. A drop reconnects with backoff; a full receiver is a `busy` state with a polite delay; the time
limit stops the link. Listen only: everything sent goes through `protocol`'s builders.
"""

import asyncio
import contextlib
import random
from collections.abc import Awaitable, Callable

from sruti.config import LinkConfig, ReceiverConfig
from sruti.events import AudioBlock, Bus, Level, LinkState, RawMessage
from sruti.receiver import protocol
from sruti.receiver.backoff import busy_delay, reconnect_delay
from sruti.receiver.capture import sanitize
from sruti.receiver.transport import Connector, Transport, TransportClosed, TransportEnded

# Not yet observed on a receiver; the names the KiwiSDR web client handles for its session limits.
TIME_LIMIT_SIGNALS = ("inactivity_timeout", "ip_limit")


class _Refused(Exception):
    def __init__(self, status: protocol.ReceiverStatus):
        super().__init__(status.kind)
        self.status = status


class _TimeLimit(Exception):
    pass


class Link:
    def __init__(self, bus: Bus, receiver: ReceiverConfig, link: LinkConfig, connector: Connector, *,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                 rand: Callable[[], float] = random.random):
        self.bus = bus
        self.receiver = receiver
        self.config = link
        self.connector = connector
        self.sleep = sleep
        self.rand = rand
        self.rate = 12000.0
        self.frames = 0
        self.truncated = 0
        self.connections = 0
        self._stop = asyncio.Event()
        self._transport: Transport | None = None
        self._compressed_reported = False

    # ------------------------------------------------------------ control

    def stop(self) -> None:
        self._stop.set()

    async def drop(self) -> None:
        """Close the current connection as if the network dropped it (for the live reconnect check)."""
        if self._transport is not None:
            await self._transport.close()

    def _state(self, state, **kw) -> None:
        self.bus.publish(LinkState(self.bus.now(), state, **kw))

    async def _wait(self, seconds: float) -> bool:
        """Sleep, but wake early on stop. True if stopped."""
        sleeper = asyncio.ensure_future(self.sleep(seconds))
        stopper = asyncio.ensure_future(self._stop.wait())
        await asyncio.wait({sleeper, stopper}, return_when=asyncio.FIRST_COMPLETED)
        for task in (sleeper, stopper):
            task.cancel()
        return self._stop.is_set()

    # ------------------------------------------------------------ the loop

    async def run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            self._state("connecting", detail=self.receiver.host_port)
            try:
                stopped = await self._session()
            except _Refused as refused:
                attempt += 1
                delay = busy_delay(attempt, self.config.reconnect_initial_s, self.config.reconnect_max_s,
                                   self.config.busy_retry_s, self.rand)
                self._state("busy", detail=refused.status.detail or refused.status.kind, retry_in_s=round(delay, 1))
                if await self._wait(delay):
                    break
                continue
            except _TimeLimit as limit:
                self._state("time_limit", detail=str(limit))
                return
            except TransportEnded:
                self._state("ended")
                return
            except TransportClosed as closed:
                if self._stop.is_set():
                    break
                attempt = 1 if listened_reset(closed) else attempt + 1
                delay = reconnect_delay(attempt, self.config.reconnect_initial_s, self.config.reconnect_max_s,
                                        self.rand)
                self._state("reconnecting", detail=str(closed), attempt=attempt, retry_in_s=round(delay, 1))
                if await self._wait(delay):
                    break
                continue
            if stopped:
                break
        self._state("stopped")

    async def _session(self) -> bool:
        """One connection, until it closes or the link stops. True if stopped by the user."""
        transport = await self.connector(self.receiver.host_port)
        self.connections += 1
        self._transport = transport
        listening = False
        keepalive = asyncio.ensure_future(self._keepalive(transport))
        try:
            for msg in protocol.setup(self.receiver.identity, self.receiver.freq_khz, self.receiver.passband):
                await self._send(transport, msg)
            while not self._stop.is_set():
                receive = asyncio.ensure_future(transport.recv())
                stopper = asyncio.ensure_future(self._stop.wait())
                done, _ = await asyncio.wait({receive, stopper}, return_when=asyncio.FIRST_COMPLETED)
                stopper.cancel()
                if receive not in done:
                    receive.cancel()
                    return True
                data = receive.result()
                tag, body = protocol.split_frame(data)
                if tag == "SND":
                    if self._audio(body) and not listening:
                        listening = True
                        self._state("listening", detail=f"{self.receiver.freq_khz:g} kHz")
                else:
                    await self._text(transport, data)
            return True
        except TransportClosed as closed:
            closed.listened = listening  # lets run() restart the backoff after a good stretch
            raise
        finally:
            keepalive.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive
            self._transport = None
            with contextlib.suppress(Exception):
                await transport.close()

    async def _keepalive(self, transport: Transport) -> None:
        with contextlib.suppress(TransportClosed):
            while True:
                await asyncio.sleep(self.config.keepalive_s)
                await transport.send(protocol.keepalive())

    async def _send(self, transport: Transport, msg: str) -> None:
        self.bus.publish(RawMessage(self.bus.now(), "→", sanitize(msg)))
        await transport.send(msg)

    def _audio(self, body: bytes) -> bool:
        frame = protocol.unpack_snd(body)
        if frame is None:
            self.truncated += 1
            return False
        now = self.bus.now()
        self.bus.publish(Level(now, round(frame.dbm, 1)))
        if frame.compressed:
            if not self._compressed_reported:
                self._compressed_reported = True
                self._state("listening", detail="the receiver sends compressed audio despite compression=0; "
                                                "frames ignored")
            return False
        self.frames += 1
        self.bus.publish(AudioBlock(now, frame.seq, frame.pcm16le, self.rate))
        return True

    async def _text(self, transport: Transport, data: bytes) -> None:
        text = data.decode("utf-8", "replace")
        self.bus.publish(RawMessage(self.bus.now(), "←", sanitize(text)))
        params = protocol.parse_msg(text)
        if params is None:
            return
        status = protocol.receiver_status(params)
        if status is not None:
            raise _Refused(status)
        for name in TIME_LIMIT_SIGNALS:
            if name in params:
                raise _TimeLimit(f"{name}={params[name]}")
        if params.get("sample_rate"):
            with contextlib.suppress(ValueError):
                self.rate = float(params["sample_rate"])
        if params.get("audio_rate"):
            with contextlib.suppress(ValueError):
                await self._send(transport, protocol.audio_rate_ok(int(params["audio_rate"])))


def listened_reset(closed: TransportClosed) -> bool:
    """A connection that streamed audio before dropping starts the backoff over."""
    return bool(getattr(closed, "listened", False))
