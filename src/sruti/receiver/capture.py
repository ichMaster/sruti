"""The raw capture and its WAV (ARCHITECTURE §The receiver): what a recording is, and what the fake
receiver replays.

A capture is JSONL, one `{t, ws, dir, msg}` object per text message on the socket. Captures get committed
as fixtures, so they are sanitized: the owner's address is masked and the receiver's configuration blobs
(its owner's contact details, band plans) keep only their size. `SET keepalive` is left out.
"""

import json
import pathlib
import wave

CONFIG_BLOBS = ("load_cfg", "load_dxcfg", "load_dxcomm_cfg")


def sanitize(msg: str) -> str:
    """Mask `client_public_ip` anywhere in a MSG; reduce the config blobs to `omitted:<size>`. Idempotent."""
    if not msg.startswith("MSG "):
        return msg
    pairs = []
    for pair in msg[4:].split(" "):
        name, eq, value = pair.partition("=")
        if name == "client_public_ip" and eq:
            pair = "client_public_ip=0.0.0.0"
        elif name in CONFIG_BLOBS and eq and not value.startswith("omitted:"):
            pair = f"{name}=omitted:{len(value)}"
        pairs.append(pair)
    return "MSG " + " ".join(pairs)


class CaptureWriter:
    """Appends sanitized text messages to a JSONL capture."""

    def __init__(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("a", encoding="utf-8")

    def write(self, t: float, direction: str, msg: str, ws: str = "SND") -> None:
        if msg == "SET keepalive":
            return
        record = {"t": round(t, 3), "ws": ws, "dir": direction, "msg": sanitize(msg)}
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class WavWriter:
    """Mono 16-bit WAV at the receiver's nominal audio rate; the header is fixed up on close."""

    def __init__(self, path: pathlib.Path, rate: int = 12000):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._wav = wave.open(str(path), "wb")  # noqa: SIM115 - closed by close()
        self._wav.setnchannels(1)
        self._wav.setsampwidth(2)
        self._wav.setframerate(rate)

    def write(self, pcm16le: bytes) -> None:
        self._wav.writeframes(pcm16le)

    def close(self) -> None:
        self._wav.close()


def read_capture(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_wav(path: pathlib.Path) -> tuple[int, bytes]:
    """(rate, 16-bit little-endian mono samples)."""
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError(f"{path}: expected mono 16-bit PCM")
        return wav.getframerate(), wav.readframes(wav.getnframes())
