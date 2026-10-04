import json
import pathlib
from array import array

import pytest

from sruti.receiver.capture import CaptureWriter, WavWriter, read_capture, read_wav, sanitize

RECORDINGS = pathlib.Path(__file__).resolve().parent.parent / "specification" / "examples" / "recordings"


@pytest.mark.parametrize("raw, want", [
    ("MSG client_public_ip=203.0.113.7", "MSG client_public_ip=0.0.0.0"),
    ("MSG rx_chans=8 client_public_ip=203.0.113.7", "MSG rx_chans=8 client_public_ip=0.0.0.0"),
    ("MSG load_cfg=%7b%22admin_email%22%7d cfg_loaded", "MSG load_cfg=omitted:23 cfg_loaded"),
    ("MSG load_dxcfg=abc load_dxcomm_cfg=abcd", "MSG load_dxcfg=omitted:3 load_dxcomm_cfg=omitted:4"),
    ("MSG audio_rate=12000", "MSG audio_rate=12000"),
    ("SET mod=cw low_cut=300 high_cut=700 freq=7027.500", "SET mod=cw low_cut=300 high_cut=700 freq=7027.500"),
])
def test_sanitize(raw, want):
    assert sanitize(raw) == want


def test_sanitize_is_idempotent():
    once = sanitize("MSG load_cfg=%7bxxxxxxxx%7d client_public_ip=1.2.3.4")
    assert sanitize(once) == once


def test_fixture_captures_are_already_sanitized():
    for path in RECORDINGS.glob("*.jsonl"):
        for record in read_capture(path):
            assert sanitize(record["msg"]) == record["msg"]


def test_capture_round_trip_skips_keepalive(tmp_path):
    writer = CaptureWriter(tmp_path / "c.jsonl")
    writer.write(1.0, "→", "SET auth t=kiwi p=")
    writer.write(1.1, "→", "SET keepalive")
    writer.write(1.2, "←", "MSG client_public_ip=198.51.100.9 rx_chans=8")
    writer.close()
    assert read_capture(tmp_path / "c.jsonl") == [
        {"t": 1.0, "ws": "SND", "dir": "→", "msg": "SET auth t=kiwi p="},
        {"t": 1.2, "ws": "SND", "dir": "←", "msg": "MSG client_public_ip=0.0.0.0 rx_chans=8"},
    ]
    assert all(json.loads(line) for line in (tmp_path / "c.jsonl").read_text(encoding="utf-8").splitlines())


def test_wav_round_trip(tmp_path):
    pcm = array("h", [0, 100, -100, 32767, -32768]).tobytes()
    writer = WavWriter(tmp_path / "a.wav", rate=12000)
    writer.write(pcm[:4])
    writer.write(pcm[4:])
    writer.close()
    assert read_wav(tmp_path / "a.wav") == (12000, pcm)


def test_fixture_wav_reads():
    rate, pcm = read_wav(RECORDINGS / "cq.wav")
    assert rate == 12000 and len(pcm) // 2 > 12000 * 170
