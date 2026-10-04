import asyncio
import pathlib
from itertools import count

import pytest

from sruti.config import LinkConfig, ReceiverConfig
from sruti.events import AudioBlock, Bus, LinkState, RawMessage
from sruti.receiver import protocol
from sruti.receiver.backoff import busy_delay, reconnect_delay
from sruti.receiver.capture import read_capture, read_wav
from sruti.receiver.fake import Behaviour, FakeReceiver
from sruti.receiver.link import Link

RECORDINGS = pathlib.Path(__file__).resolve().parent.parent / "specification" / "examples" / "recordings"
LINK = LinkConfig(reconnect_initial_s=2.0, reconnect_max_s=60.0, busy_retry_s=30.0, keepalive_s=3600.0)


def run_link(fake: FakeReceiver, *, stop_after_blocks: int | None = None, link_config: LinkConfig = LINK):
    """Run the link over the fake receiver to its end; return (events, sleeps, link)."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        await asyncio.sleep(0)

    async def scenario():
        ticks = count()
        bus = Bus(clock=lambda: float(next(ticks)))
        queue = bus.subscribe()
        link = Link(bus, ReceiverConfig(freq_khz=7033.05), link_config, fake.connect, sleep=fake_sleep,
                    rand=lambda: 0.5)
        events = []

        async def collect():
            blocks = 0
            while True:
                event = await queue.get()
                events.append(event)
                if isinstance(event, AudioBlock):
                    blocks += 1
                    if stop_after_blocks is not None and blocks == stop_after_blocks:
                        link.stop()
                if isinstance(event, LinkState) and event.state in ("ended", "stopped", "time_limit"):
                    return

        collector = asyncio.ensure_future(collect())
        await asyncio.wait_for(link.run(), timeout=60)
        await asyncio.wait_for(collector, timeout=5)
        return events, link

    events, link = asyncio.run(scenario())
    return events, sleeps, link


def states(events):
    return [e.state for e in events if isinstance(e, LinkState)]


def audio(events) -> bytes:
    return b"".join(e.pcm16le for e in events if isinstance(e, AudioBlock))


def cq_fake(**kw) -> FakeReceiver:
    return FakeReceiver.from_recording(RECORDINGS / "cq.wav", RECORDINGS / "cq.jsonl", **kw)


# ---------------------------------------------------------------- backoff

def test_reconnect_delay_doubles_and_caps():
    delays = [reconnect_delay(n, 2.0, 60.0, lambda: 0.5) for n in range(1, 8)]
    assert delays == [2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]


def test_jitter_stays_within_a_quarter():
    assert reconnect_delay(1, 2.0, 60.0, lambda: 0.0) == pytest.approx(1.5)
    assert reconnect_delay(1, 2.0, 60.0, lambda: 1.0) == pytest.approx(2.5)


def test_busy_delay_never_below_the_floor():
    assert busy_delay(1, 2.0, 60.0, 30.0, lambda: 0.0) == 30.0
    assert busy_delay(7, 2.0, 60.0, 30.0, lambda: 1.0) == pytest.approx(75.0)


# ---------------------------------------------------------------- replay

def test_replay_yields_the_same_audio_and_messages():
    fake = cq_fake()
    events, sleeps, _ = run_link(fake)
    _, wav_pcm = read_wav(RECORDINGS / "cq.wav")
    assert audio(events) == wav_pcm
    received = [e.msg for e in events if isinstance(e, RawMessage) and e.direction == "←"]
    assert received == [r["msg"] for r in read_capture(RECORDINGS / "cq.jsonl") if r["dir"] == "←"]
    assert states(events) == ["connecting", "listening", "ended"]
    assert sleeps == [] and fake.connections == 1 and fake.max_open == 1


def test_the_link_sends_only_documented_messages():
    fake = cq_fake()
    run_link(fake)
    assert {protocol.message_name(m) for m in fake.sent_log} <= protocol.DOCUMENTED
    assert fake.sent_log[:3] == ["SET auth t=kiwi p=", "SERVER DE CLIENT sruti SND", "SET ident_user=sruti"]
    assert "SET mod=cw low_cut=300 high_cut=700 freq=7033.050" in fake.sent_log
    assert "SET AR OK in=12000 out=44100" in fake.sent_log


def test_outgoing_messages_are_published_for_the_inspector():
    events, _, _ = run_link(cq_fake())
    sent = [e.msg for e in events if isinstance(e, RawMessage) and e.direction == "→"]
    assert sent[0] == "SET auth t=kiwi p=" and "SET compression=0" in sent


# ---------------------------------------------------------------- drops, busy, stop, limits

def test_a_drop_reconnects_without_losing_or_repeating_audio():
    fake = cq_fake(script=[Behaviour(drop_after_frames=100), Behaviour()])
    events, sleeps, _ = run_link(fake)
    assert states(events) == ["connecting", "listening", "reconnecting", "connecting", "listening", "ended"]
    reconnecting = next(e for e in events if isinstance(e, LinkState) and e.state == "reconnecting")
    assert reconnecting.attempt == 1 and reconnecting.retry_in_s == 2.0
    assert sleeps == [2.0]
    _, wav_pcm = read_wav(RECORDINGS / "cq.wav")
    assert audio(events) == wav_pcm
    assert fake.connections == 2 and fake.max_open == 1


def test_a_full_receiver_waits_politely():
    fake = cq_fake(script=[Behaviour(busy=True), Behaviour(busy=True), Behaviour()])
    events, sleeps, _ = run_link(fake)
    busy = [e for e in events if isinstance(e, LinkState) and e.state == "busy"]
    assert len(busy) == 2 and all(e.retry_in_s >= LINK.busy_retry_s for e in busy)
    assert sleeps and all(s >= LINK.busy_retry_s for s in sleeps)
    assert states(events)[-2:] == ["listening", "ended"]


def test_stop_ends_the_session_cleanly():
    fake = cq_fake()
    events, _, link = run_link(fake, stop_after_blocks=50)
    assert states(events)[-1] == "stopped"
    assert fake.open_now == 0
    assert 50 <= link.frames < len(fake.frames)


def test_time_limit_stops_without_reconnecting():
    fake = cq_fake(script=[Behaviour(extra=["MSG inactivity_timeout=1"])])
    events, sleeps, _ = run_link(fake)
    assert states(events) == ["connecting", "time_limit"]
    assert fake.connections == 1 and sleeps == []


def test_keepalive_is_sent_on_its_interval():
    class Recorder:
        def __init__(self):
            self.sent = []

        async def send(self, text):
            self.sent.append(text)

    async def scenario():
        link = Link(Bus(), ReceiverConfig(), LinkConfig(keepalive_s=0.01), connector=None)
        transport = Recorder()
        task = asyncio.ensure_future(link._keepalive(transport))
        await asyncio.sleep(0.06)
        task.cancel()
        return transport.sent

    sent = asyncio.run(scenario())
    assert len(sent) >= 3 and set(sent) == {"SET keepalive"}
