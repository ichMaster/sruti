"""Headless listening: run the receiver link, print what happens, optionally record WAV + capture.

`sruti listen` from v1.1: link states, the signal level every 10 s, and the raw messages with `--raw`.
Characters arrive with the decoder in v1.2. A recording is the v0.1 format — the pair the fake receiver
replays.
"""

import asyncio
import contextlib
import datetime
import pathlib
import signal
import sys
import time
from collections.abc import Callable
from typing import TextIO

from sruti.config import Config, ReceiverConfig
from sruti.events import AudioBlock, Bus, Level, LinkState, RawMessage
from sruti.receiver.capture import CaptureWriter, WavWriter
from sruti.receiver.link import Link
from sruti.receiver.transport import Connector

FINAL_STATES = ("stopped", "ended", "time_limit")


def recording_stem(started: float, receiver: ReceiverConfig) -> str:
    """`<started>-<receiver>-<freq>`, as the session store will name its files."""
    stamp = datetime.datetime.fromtimestamp(started, tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    host = receiver.host_port.split(":", 1)[0]
    return f"{stamp}-{host}-{receiver.freq_khz:g}"


class Recorder:
    """Writes the link's raw messages to a JSONL capture and its audio to a WAV beside it."""

    def __init__(self, directory: pathlib.Path, stem: str):
        self.capture_path = directory / f"{stem}.jsonl"
        self.wav_path = directory / f"{stem}.wav"
        self._capture = CaptureWriter(self.capture_path)
        self._wav: WavWriter | None = None

    def write(self, event) -> None:
        if isinstance(event, RawMessage):
            self._capture.write(event.t, event.direction, event.msg, event.ws)
        elif isinstance(event, AudioBlock):
            if self._wav is None:
                rate = 12000 if 11500 < event.rate < 12500 else round(event.rate)  # the nominal rate
                self._wav = WavWriter(self.wav_path, rate)
            self._wav.write(event.pcm16le)

    def close(self) -> None:
        self._capture.close()
        if self._wav is not None:
            self._wav.close()


def _clock_text(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, tz=datetime.UTC).astimezone().strftime("%H:%M:%S")


def _state_line(event: LinkState) -> str:
    parts = [_clock_text(event.t), event.state]
    if event.attempt is not None:
        parts.append(f"attempt {event.attempt}")
    if event.retry_in_s is not None:
        parts.append(f"retry in {event.retry_in_s:g} s")
    if event.detail:
        parts.append(f"({event.detail})")
    return " ".join(parts)


async def listen(config: Config, receiver: ReceiverConfig, connector: Connector, *, out: TextIO = sys.stdout,
                 record_dir: pathlib.Path | None = None, raw: bool = False, drop_after: float | None = None,
                 clock: Callable[[], float] = time.time, level_every_s: float = 10.0,
                 sleep=asyncio.sleep, stop_after_frames: int | None = None) -> str:
    """Run until the link stops, ends or hits the time limit; return the final state.

    `stop_after_frames` stops the link after that many audio frames (for tests).
    """
    bus = Bus(clock)
    queue = bus.subscribe()
    link = Link(bus, receiver, config.link, connector, sleep=sleep)
    recorder = Recorder(record_dir, recording_stem(clock(), receiver)) if record_dir else None
    if recorder:
        print(f"recording to {recorder.wav_path} and {recorder.capture_path.name}", file=out, flush=True)
    listening = asyncio.Event()
    final = {"state": "stopped"}

    async def show() -> None:
        frames = samples = 0
        last_dbm = None
        next_level = None
        while True:
            event = await queue.get()
            if recorder:
                recorder.write(event)
            if isinstance(event, LinkState):
                print(_state_line(event), file=out, flush=True)
                if event.state == "listening":
                    listening.set()
                if event.state in FINAL_STATES:
                    final["state"] = event.state
                    return
            elif isinstance(event, AudioBlock):
                frames += 1
                samples += len(event.pcm16le) // 2
                if stop_after_frames is not None and frames == stop_after_frames:
                    link.stop()
            elif isinstance(event, Level):
                last_dbm = event.dbm
                if next_level is None:
                    next_level = event.t + level_every_s
                elif event.t >= next_level:
                    next_level = event.t + level_every_s
                    print(f"{_clock_text(event.t)} level {last_dbm:.1f} dBm · {frames} frames · {samples} samples",
                          file=out, flush=True)
            elif isinstance(event, RawMessage) and raw:
                print(f"{event.direction} {event.msg}", file=out, flush=True)

    async def drop_once() -> None:
        await listening.wait()
        await asyncio.sleep(drop_after)
        print(f"{_clock_text(clock())} dropping the connection on purpose (--drop-after)", file=out, flush=True)
        await link.drop()

    loop = asyncio.get_running_loop()
    with contextlib.suppress(NotImplementedError, RuntimeError):
        loop.add_signal_handler(signal.SIGINT, link.stop)
    shower = asyncio.ensure_future(show())
    dropper = asyncio.ensure_future(drop_once()) if drop_after is not None else None
    try:
        await link.run()
        await shower
    finally:
        if dropper:
            dropper.cancel()
        if not shower.done():
            shower.cancel()
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.remove_signal_handler(signal.SIGINT)
        if recorder:
            recorder.close()
    print(f"{_clock_text(clock())} {link.frames} audio frames over {link.connections} connection(s)"
          + (f", {link.truncated} truncated" if link.truncated else ""), file=out, flush=True)
    return final["state"]
