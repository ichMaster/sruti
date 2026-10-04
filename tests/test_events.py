import asyncio
from array import array

from sruti.events import AudioBlock, Bus, Level, LinkState, RawMessage


def test_bus_delivers_in_order_to_every_subscriber():
    async def scenario():
        bus = Bus(clock=lambda: 100.0)
        first, second = bus.subscribe(), bus.subscribe()
        events = [LinkState(bus.now(), "connecting"), Level(bus.now(), -95.5),
                  RawMessage(bus.now(), "←", "MSG audio_rate=12000")]
        for event in events:
            bus.publish(event)
        got_first = [first.get_nowait() for _ in events]
        got_second = [second.get_nowait() for _ in events]
        return events, got_first, got_second

    events, got_first, got_second = asyncio.run(scenario())
    assert got_first == events and got_second == events


def test_unsubscribed_queue_gets_nothing_more():
    async def scenario():
        bus = Bus()
        queue = bus.subscribe()
        bus.unsubscribe(queue)
        bus.publish(Level(0.0, -100.0))
        return queue.empty()

    assert asyncio.run(scenario())


def test_injected_clock_stamps_events():
    ticks = iter([10.0, 10.5])
    bus = Bus(clock=lambda: next(ticks))
    assert [bus.now(), bus.now()] == [10.0, 10.5]


def test_audio_block_round_trips_samples():
    samples = array("h", [0, 1, -1, 32767, -32768])
    block = AudioBlock(t=1.0, seq=7, pcm16le=samples.tobytes(), rate=12000.0)
    assert block.samples() == samples
