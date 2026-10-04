import pathlib
import re
from array import array

import pytest

from sruti.receiver import protocol as p
from sruti.receiver.capture import read_capture

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORDINGS = ROOT / "specification" / "examples" / "recordings"
ARCHITECTURE = ROOT / "specification" / "ARCHITECTURE.md"


def documented_in_architecture() -> set[str]:
    """Message names in backticks in the receiver section's message table (`SET x`, `MSG y`, bare MSG names)."""
    section = ARCHITECTURE.read_text(encoding="utf-8").split("## The receiver", 1)[1].split("\n## ", 1)[0]
    names = set()
    for row in (line for line in section.splitlines() if line.startswith(("| →", "| ←"))):
        cells = re.split(r"(?<!\\)\|", row)  # split on unescaped pipes; `\|` stays inside a cell
        for code in re.findall(r"`([^`]+)`", cells[2]):  # the Message column only
            words = code.replace("\\|", "|").split(" ")
            if words[0] == "SERVER":
                names.add("SERVER DE CLIENT")
            elif words[0] in ("SET", "MSG") and len(words) > 1:
                names.add(f"{words[0]} {words[1].split('=')[0]}")
            elif re.fullmatch(r"[A-Za-z_]+", words[0]):
                names.add(f"MSG {words[0]}")
    return names


# ---------------------------------------------------------------- outgoing

def test_builders_produce_the_documented_messages():
    assert p.auth() == "SET auth t=kiwi p="
    assert p.greeting("sruti") == "SERVER DE CLIENT sruti SND"
    assert p.ident("sruti") == "SET ident_user=sruti"
    assert p.tune(7027.5, (300, 700)) == "SET mod=cw low_cut=300 high_cut=700 freq=7027.500"
    assert p.compression_off() == "SET compression=0"
    assert p.audio_rate_ok(12000) == "SET AR OK in=12000 out=44100"
    assert p.keepalive() == "SET keepalive"


def test_every_outgoing_message_is_documented_and_the_set_matches_architecture():
    sent = [*p.setup("sruti", 7027.5, (300, 700)), p.audio_rate_ok(12000), p.keepalive()]
    assert {p.message_name(m) for m in sent} == p.DOCUMENTED
    outgoing_in_table = {n for n in documented_in_architecture() if not n.startswith("MSG ")}
    assert outgoing_in_table == p.DOCUMENTED


def test_tune_is_the_signal_frequency_with_no_passband_shift():
    assert "freq=14100.000" in p.tune(14100, (300, 700))


# ---------------------------------------------------------------- incoming

def test_parse_msg_decodes_values_and_flags():
    assert p.parse_msg("MSG audio_init=0 audio_rate=12000") == {"audio_init": "0", "audio_rate": "12000"}
    assert p.parse_msg("MSG cfg_loaded") == {"cfg_loaded": None}
    params = p.parse_msg("MSG last_community_download=Downloads%20enabled.")
    assert params == {"last_community_download": "Downloads enabled."}
    assert p.parse_msg("SET keepalive") is None


@pytest.mark.parametrize("msg, kind", [
    ("MSG badp=1", "busy"),
    ("MSG too_busy=6", "too_busy"),
    ("MSG down", "down"),
    ("MSG redirect=http%3a//other.example:8073", "redirect"),
])
def test_refusals_map_to_states(msg, kind):
    status = p.receiver_status(p.parse_msg(msg))
    assert status is not None and status.kind == kind


def test_badp_zero_is_not_a_refusal():
    assert p.receiver_status(p.parse_msg("MSG badp=0")) is None


def test_every_fixture_message_parses_and_is_in_the_architecture_table():
    names = set()
    for path in sorted(RECORDINGS.glob("*.jsonl")):
        for record in read_capture(path):
            msg = record["msg"]
            if record["dir"] == "←":
                params = p.parse_msg(msg)
                assert params is not None, msg
                names |= {f"MSG {name}" for name in params}
            else:
                names.add(p.message_name(msg))
    assert len(names) == 43
    assert names - documented_in_architecture() == set()


# ---------------------------------------------------------------- SND frames

def test_unpack_snd_reads_sequence_level_and_big_endian_samples():
    samples = array("h", [1, -2, 300, -32768, 32767])
    big = array("h", samples)
    big.byteswap()
    body = bytes([0]) + (1234).to_bytes(4, "little") + (320).to_bytes(2, "big") + big.tobytes()
    frame = p.unpack_snd(body)
    assert frame.seq == 1234
    assert frame.dbm == pytest.approx(-95.0)
    assert frame.pcm16le == samples.tobytes()
    assert not frame.compressed


def test_truncated_frame_is_dropped_and_odd_byte_ignored():
    assert p.unpack_snd(b"\x00\x01\x02") is None
    body = bytes([0]) + (1).to_bytes(4, "little") + (300).to_bytes(2, "big") + b"\x00\x05\x07"
    assert p.unpack_snd(body).pcm16le == array("h", [5]).tobytes()


def test_compressed_frame_is_reported_without_samples():
    body = bytes([p.SND_FLAG_COMPRESSED]) + (9).to_bytes(4, "little") + (300).to_bytes(2, "big") + b"\x12\x34"
    frame = p.unpack_snd(body)
    assert frame.compressed and frame.pcm16le == b"" and frame.seq == 9


def test_pack_and_unpack_round_trip():
    pcm = array("h", range(-500, 500, 7)).tobytes()
    tag, body = p.split_frame(p.pack_snd(42, -101.3, pcm))
    frame = p.unpack_snd(body)
    assert tag == "SND" and frame.seq == 42 and frame.pcm16le == pcm
    assert frame.dbm == pytest.approx(-101.3, abs=0.05)
