import asyncio
import io
import pathlib
from itertools import count

from sruti.cli import build_parser
from sruti.config import Config, ReceiverConfig
from sruti.listen import listen, recording_stem
from sruti.receiver.capture import read_capture, read_wav
from sruti.receiver.fake import FakeReceiver

RECORDINGS = pathlib.Path(__file__).resolve().parent.parent / "specification" / "examples" / "recordings"
RECEIVER = ReceiverConfig(host_port="sdr.example.org:8073", freq_khz=7033.05)


async def _no_wait(seconds: float) -> None:
    await asyncio.sleep(0)


def run(fake: FakeReceiver, **kw) -> tuple[str, str]:
    out = io.StringIO()
    ticks = count(1_000_000, 0.05)  # 20 events per simulated second
    final = asyncio.run(asyncio.wait_for(
        listen(Config(), RECEIVER, fake.connect, out=out, clock=lambda: next(ticks), sleep=_no_wait, **kw),
        timeout=60))
    return final, out.getvalue()


def cq_fake() -> FakeReceiver:
    return FakeReceiver.from_recording(RECORDINGS / "cq.wav", RECORDINGS / "cq.jsonl")


def test_listen_prints_states_and_levels():
    final, text = run(cq_fake())
    assert final == "ended"
    assert " connecting " in text and " listening " in text and " ended" in text
    assert " level -95.0 dBm · " in text
    assert "audio frames over 1 connection(s)" in text


def test_a_recording_replays_to_the_same_audio_and_messages(tmp_path):
    final, text = run(cq_fake(), record_dir=tmp_path)
    assert final == "ended" and "recording to" in text
    wav = next(tmp_path.glob("*.wav"))
    capture = wav.with_suffix(".jsonl")
    assert read_wav(wav) == read_wav(RECORDINGS / "cq.wav")
    original_received = [r["msg"] for r in read_capture(RECORDINGS / "cq.jsonl") if r["dir"] == "←"]
    assert [r["msg"] for r in read_capture(capture) if r["dir"] == "←"] == original_received
    sent = [r["msg"] for r in read_capture(capture) if r["dir"] == "→"]
    assert sent[0] == "SET auth t=kiwi p=" and "SET keepalive" not in sent
    # and the recording itself replays through the fake receiver
    replay_final, _ = run(FakeReceiver.from_recording(wav, capture), record_dir=tmp_path / "again")
    assert replay_final == "ended"
    assert read_wav(next((tmp_path / "again").glob("*.wav"))) == read_wav(wav)


def test_drop_after_reconnects_and_keeps_the_audio(tmp_path):
    final, text = run(cq_fake(), record_dir=tmp_path, drop_after=0)
    assert final == "ended"
    assert "dropping the connection on purpose" in text and " reconnecting attempt 1" in text
    assert "over 2 connection(s)" in text
    assert read_wav(next(tmp_path.glob("*.wav"))) == read_wav(RECORDINGS / "cq.wav")


def test_stop_leaves_valid_files(tmp_path):
    final, text = run(cq_fake(), record_dir=tmp_path, stop_after_frames=40)
    assert final == "stopped" and " stopped" in text
    rate, pcm = read_wav(next(tmp_path.glob("*.wav")))
    assert rate == 12000 and len(pcm) >= 40 * 512 * 2
    assert read_capture(next(tmp_path.glob("*.jsonl")))


def test_raw_prints_both_directions():
    _, text = run(cq_fake(), raw=True)
    assert "→ SET auth t=kiwi p=" in text and "← MSG audio_init=0 audio_rate=12000" in text


def test_cli_record_and_raw_arguments():
    args = build_parser().parse_args(["listen", "--receiver", "a.org:8073", "--freq", "14100",
                                      "--record", "var/recordings", "--raw"])
    assert args.record == pathlib.Path("var/recordings") and args.raw and args.drop_after is None


def test_recording_stem_is_started_receiver_freq():
    assert recording_stem(0.0, RECEIVER) == "19700101-000000-sdr.example.org-7033.05"
