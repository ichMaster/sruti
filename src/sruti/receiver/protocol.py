"""The KiwiSDR audio-channel protocol, pure: the messages sruti sends, parsing what the receiver sends,
and unpacking SND audio frames (ARCHITECTURE §The receiver).

Listen only: the builders below are the only messages sruti ever sends, and DOCUMENTED names them.
"""

import sys
import urllib.parse
from array import array
from dataclasses import dataclass

SND_FLAG_COMPRESSED = 0x10
AR_OUT_RATE = 44100

DOCUMENTED = frozenset({
    "SET auth", "SERVER DE CLIENT", "SET ident_user", "SET mod", "SET agc", "SET compression", "SET AR",
    "SET squelch", "SET genattn", "SET gen", "SET keepalive",
})


# ---------------------------------------------------------------- outgoing

def auth() -> str:
    return "SET auth t=kiwi p="


def greeting(identity: str) -> str:
    return f"SERVER DE CLIENT {identity} SND"


def ident(identity: str) -> str:
    return f"SET ident_user={urllib.parse.quote(identity)}"


def tune(freq_khz: float, passband: tuple[int, int]) -> str:
    """CW mode at the signal's own frequency; the receiver puts it on a tone near 500 Hz."""
    low, high = passband
    return f"SET mod=cw low_cut={low} high_cut={high} freq={freq_khz:.3f}"


def agc() -> str:
    return "SET agc=1 hang=0 thresh=-100 slope=6 decay=1000 manGain=50"


def compression_off() -> str:
    return "SET compression=0"


def audio_rate_ok(rate: int) -> str:
    return f"SET AR OK in={rate} out={AR_OUT_RATE}"


def squelch_off() -> str:
    return "SET squelch=0 max=0"


def genattn_off() -> str:
    return "SET genattn=0"


def gen_off() -> str:
    return "SET gen=0 mix=-1"


def keepalive() -> str:
    return "SET keepalive"


def setup(identity: str, freq_khz: float, passband: tuple[int, int]) -> list[str]:
    """What the browser page sends right after the socket opens, in its order."""
    return [auth(), greeting(identity), ident(identity), tune(freq_khz, passband), agc(), compression_off(),
            squelch_off(), genattn_off(), gen_off()]


def message_name(msg: str) -> str:
    """`SET mod`, `SERVER DE CLIENT`, `MSG audio_rate` (first parameter), or the bare tag."""
    tag, _, body = msg.partition(" ")
    if tag == "SET":
        return f"SET {body.split(' ')[0].split('=')[0]}"
    if tag == "SERVER":
        return "SERVER DE CLIENT"
    if tag == "MSG" and body:
        return f"MSG {body.split(' ')[0].split('=')[0]}"
    return tag


# ---------------------------------------------------------------- incoming text

def parse_msg(msg: str) -> dict[str, str | None] | None:
    """`MSG a=1 b c=%20x` → {"a": "1", "b": None, "c": " x"}; None for anything that is not a MSG."""
    tag, _, body = msg.partition(" ")
    if tag != "MSG":
        return None
    params: dict[str, str | None] = {}
    for pair in body.split(" "):
        if not pair:
            continue
        name, eq, value = pair.partition("=")
        params[name] = urllib.parse.unquote(value) if eq else None
    return params


@dataclass(frozen=True)
class ReceiverStatus:
    """A refusal or redirection from the receiver."""

    kind: str  # "busy" | "too_busy" | "down" | "redirect"
    detail: str = ""


def receiver_status(params: dict[str, str | None]) -> ReceiverStatus | None:
    if params.get("badp") == "1":
        return ReceiverStatus("busy", "all channels without a password are taken")
    if "too_busy" in params:
        return ReceiverStatus("too_busy", params["too_busy"] or "")
    if "down" in params:
        return ReceiverStatus("down", params["down"] or "")
    if "redirect" in params:
        return ReceiverStatus("redirect", params["redirect"] or "")
    return None


# ---------------------------------------------------------------- SND audio frames

@dataclass(frozen=True)
class SndFrame:
    flags: int
    seq: int
    dbm: float
    pcm16le: bytes
    compressed: bool = False


def split_frame(data: bytes) -> tuple[str, bytes]:
    """A WebSocket frame: a three-letter tag (`SND`, `MSG`, …) then its body."""
    return data[:3].decode("ascii", "replace"), data[3:]


def unpack_snd(body: bytes) -> SndFrame | None:
    """flags (1), sequence (4, LE), S-meter (2, BE; dBm = 0.1 × v − 127), samples (16-bit BE).

    None for a truncated frame. A compressed frame (the receiver ignored compression=0) carries no samples.
    """
    if len(body) < 7:
        return None
    flags = body[0]
    seq = int.from_bytes(body[1:5], "little")
    dbm = 0.1 * int.from_bytes(body[5:7], "big") - 127
    data = body[7:]
    if flags & SND_FLAG_COMPRESSED:
        return SndFrame(flags, seq, dbm, b"", compressed=True)
    samples = array("h")
    samples.frombytes(data[: len(data) - len(data) % 2])
    if sys.byteorder == "little":
        samples.byteswap()
    return SndFrame(flags, seq, dbm, samples.tobytes())


def pack_snd(seq: int, dbm: float, pcm16le: bytes, flags: int = 0) -> bytes:
    """The inverse of unpack_snd, with the tag: what a receiver puts on the wire (used by the fake receiver)."""
    samples = array("h")
    samples.frombytes(pcm16le)
    if sys.byteorder == "little":
        samples.byteswap()
    meter = max(0, min(0xFFFF, round((dbm + 127) * 10)))
    return b"SND" + bytes([flags]) + seq.to_bytes(4, "little") + meter.to_bytes(2, "big") + samples.tobytes()
