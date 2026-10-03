#!/usr/bin/env python3
"""v0.1 spike: decoded CW text from a public KiwiSDR, live, with a raw capture.

Opens one CW audio channel (SND) and the CW_decoder extension (EXT) on the receiver, prints the decoded
text as it arrives and writes every text message crossing the two sockets to a JSONL capture. Replay
mode prints a saved capture's text and never connects.

kiwiclient has no license (checked 2026-10-03 at jks-prv/kiwiclient 4eb733e): it is used only by this
spike, from a local checkout in var/kiwiclient that is never committed. sruti's own receiver client is
built in v1.1 from the protocol these captures show.

Setup, once:
    git clone https://github.com/jks-prv/kiwiclient.git var/kiwiclient
    git -C var/kiwiclient checkout 4eb733e6b6147f7fbeb97ced64cdac029b202d18

Listen and record (Ctrl-C to stop):
    uv run --no-project --with numpy python poc/receiver/cw_spike.py \\
        --receiver <host>:8073 --freq 14100 --out var/recordings/beacons.jsonl

Replay a capture (offline):
    python3 poc/receiver/cw_spike.py --replay var/recordings/beacons.jsonl

Capture format, one JSON object per line: {"t": epoch seconds, "ws": "SND" | "EXT", "dir": "→" sent or
"←" received, "msg": the text message exactly as on the wire}. Binary audio frames and the once-a-second
"SET keepalive" are not recorded.
"""

import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.parse
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
KIWICLIENT = ROOT / "var" / "kiwiclient"

IDENTITY = "sruti"
CW_PASSBAND = (300, 700)  # Hz above the carrier: the KiwiSDR default CW passband
TRAINING = 100  # the browser decoder's default training interval
THRESHOLD_DB = 47  # the browser decoder's default fixed threshold


# ---------------------------------------------------------------- replay (no network, no kiwiclient)

def message_type(direction: str, msg: str) -> list[str]:
    """Names of the parameters a message carries, e.g. 'EXT cw_chars' or 'SET cw_pboff'."""
    tag, _, body = msg.partition(" ")
    names = [pair.split("=", 1)[0] for pair in body.split(" ") if pair]
    if tag == "SET" and names:
        return [f"SET {names[0]}"]
    return [f"{tag} {name}" for name in names] or [tag]


def replay(path: pathlib.Path) -> int:
    counts: Counter = Counter()
    status = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            direction, msg = rec["dir"], rec["msg"]
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"\n[line {line_no}: unreadable record: {exc}]", file=sys.stderr)
            continue
        for name in message_type(direction, msg):
            counts[f"{direction} {name}"] += 1
        if direction != "←" or not msg.startswith("EXT "):
            continue
        for pair in msg[4:].split(" "):
            name, _, value = pair.partition("=")
            if name == "cw_chars":
                sys.stdout.write(urllib.parse.unquote(value))
                sys.stdout.flush()
            elif name in ("cw_wpm", "cw_train"):
                status[name] = value
    print()
    print(f"\nstatus: {status or 'none'}", file=sys.stderr)
    print("message types:", file=sys.stderr)
    for name, n in sorted(counts.items()):
        print(f"  {n:6}  {name}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- live (kiwiclient)

class Capture:
    def __init__(self, path: pathlib.Path | None):
        self._file = path.open("a", encoding="utf-8") if path else None
        self._lock = threading.Lock()

    def write(self, ws: str, direction: str, msg: str) -> None:
        if self._file is None or msg == "SET keepalive":
            return
        line = json.dumps({"t": round(time.time(), 3), "ws": ws, "dir": direction, "msg": msg},
                          ensure_ascii=False)
        with self._lock:
            self._file.write(line + "\n")
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()


def make_streams(args, capture: Capture, stop: threading.Event):
    sys.path.insert(0, str(KIWICLIENT))
    from types import SimpleNamespace

    from kiwi.client import KiwiSDRStream

    host, port = args.receiver.rsplit(":", 1)
    options = SimpleNamespace(
        server_host=host, server_port=int(port), wideband=False, socket_timeout=10,
        ws_timestamp=int(time.time()) & 0xFFFFFFFF,  # shared: it ties the EXT socket to the SND channel
        nolocal=False, admin=False, password="", tlimit_password="",
        freq_pbc=True, tlimit=None, stats=False, idx=0, wf_cal=None,
    )

    class Stream(KiwiSDRStream):
        def __init__(self, kind: str):
            super().__init__()
            self._type = kind
            self._options = options
            self._freq_offset = 0
            self._start_time = time.time()

        def _send_message(self, msg):
            capture.write(self._type, "→", msg)
            super()._send_message(msg)

        def _process_ws_message(self, message):
            tag = bytes(message[0:3]).decode("ascii", "replace")
            if tag != "SND":
                capture.write(self._type, "←", bytes(message).decode("utf-8", "replace"))
            super()._process_ws_message(message)

    class Sound(Stream):
        def __init__(self):
            super().__init__("SND")

        def _process_aud(self, body):
            pass  # the audio itself is not needed: the receiver decodes the CW

        def _setup_rx_params(self):
            self.set_name(IDENTITY)
            self.set_mod("cw", CW_PASSBAND[0], CW_PASSBAND[1], args.freq)
            self.set_agc(on=True)

    class Decoder(Stream):
        def __init__(self):
            super().__init__("EXT")

        def _setup_rx_params(self):
            # The order the KiwiSDR browser client uses: start, tone offset, speed, then the threshold,
            # which must follow cw_wpm because setting the speed re-initialises the decoder.
            self.set_name(IDENTITY)
            self._send_message("SET ext_switch_to_client=CW_decoder first_time=1 rx_chan=0")
            self._send_message(f"SET cw_start={TRAINING}")
            self._send_message(f"SET cw_pboff={args.pboff}")
            self._send_message(f"SET cw_wpm=0,{TRAINING}")
            self._send_message("SET cw_auto_thresh=0")
            self._send_message(f"SET cw_threshold={round(10 ** (THRESHOLD_DB / 10))}")

        def _process_ext(self, name, value):
            if name == "cw_chars" and value is not None:
                sys.stdout.write(value)
                sys.stdout.flush()
            elif name in ("cw_wpm", "cw_train"):
                print(f"\n[{name} {value}]", file=sys.stderr, flush=True)

        def stop_decoder(self):
            try:
                self._send_message("SET cw_stop")
            except Exception:  # noqa: BLE001, S110 - best effort on the way out
                pass

    return Sound(), Decoder()


def drive(stream, stop: threading.Event, errors: list) -> None:
    try:
        stream.connect(stream._options.server_host, stream._options.server_port)
        stream.open()
        while not stop.is_set():
            stream.run()
    except Exception as exc:  # noqa: BLE001 - report why the receiver ended the session, then stop
        if not stop.is_set():
            errors.append(f"{stream._type}: {type(exc).__name__}: {exc}")
    finally:
        stop.set()


def listen(args) -> int:
    if not (KIWICLIENT / "kiwi" / "client.py").exists():
        print(f"kiwiclient not found in {KIWICLIENT} — see the setup lines at the top of this file",
              file=sys.stderr)
        return 2
    out = pathlib.Path(args.out) if args.out else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
    capture = Capture(out)
    stop = threading.Event()
    errors: list = []
    sound, decoder = make_streams(args, capture, stop)
    print(f"{args.receiver} · {args.freq} kHz (passband centre) · cw_pboff {args.pboff} Hz"
          f"{' · capture ' + str(out) if out else ''} — Ctrl-C to stop", file=sys.stderr)

    threads = [threading.Thread(target=drive, args=(sound, stop, errors), daemon=True)]
    threads[0].start()
    time.sleep(2)  # the channel must exist before the extension attaches to it
    threads.append(threading.Thread(target=drive, args=(decoder, stop, errors), daemon=True))
    threads[1].start()
    try:
        while not stop.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    decoder.stop_decoder()
    stop.set()
    for s in (decoder, sound):
        try:
            s.close()
        except Exception:  # noqa: BLE001, S110 - best effort on the way out
            pass
    capture.close()
    print(file=sys.stderr)
    for err in errors:
        print(f"receiver ended the session — {err}", file=sys.stderr)
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--receiver", help="host:port of a public KiwiSDR")
    ap.add_argument("--freq", type=float, help="frequency in kHz, used as the passband centre")
    ap.add_argument("--pboff", type=int, default=500, help="tone offset for the decoder, Hz (default 500)")
    ap.add_argument("--out", help="write the raw capture to this JSONL file")
    ap.add_argument("--replay", help="print the text of a saved capture and exit (offline)")
    args = ap.parse_args()
    if args.replay:
        return replay(pathlib.Path(args.replay))
    if not args.receiver or args.freq is None:
        ap.error("--receiver and --freq are required to listen (or use --replay)")
    return listen(args)


if __name__ == "__main__":
    sys.exit(main())
