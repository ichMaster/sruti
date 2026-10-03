#!/usr/bin/env python3
"""v0.1 spike: CW from a public KiwiSDR's audio, decoded on the Mac, with a raw capture.

Opens one CW audio channel (SND) tuned to the signal's own frequency, records the audio as WAV beside a
JSONL capture of every text message, and decodes the WAV with sruti's prototype decoder (cw_decode.py)
when the session ends. The receiver's own CW_decoder extension (EXT) is used only with --kiwi-decoder.
Replay mode prints a saved capture's text and never connects.

kiwiclient has no license (checked 2026-10-03 at jks-prv/kiwiclient 4eb733e): it is used only by this
spike, from a local checkout in var/kiwiclient that is never committed. sruti's own receiver client is
built in v1.1 from the protocol these captures show.

Setup, once:
    git clone https://github.com/jks-prv/kiwiclient.git var/kiwiclient
    git -C var/kiwiclient checkout 4eb733e6b6147f7fbeb97ced64cdac029b202d18

Listen, record and decode (Ctrl-C to stop):
    uv run --no-project --with numpy python poc/receiver/cw_spike.py --browser-path \\
        --receiver <host>:8073 --freq 14100 \\
        --out var/recordings/beacons.jsonl --audio var/recordings/beacons.wav

Replay a capture (offline):
    python3 poc/receiver/cw_spike.py --replay var/recordings/beacons.jsonl

Capture format, one JSON object per line: {"t": epoch seconds, "ws": "SND" | "EXT", "dir": "→" sent or
"←" received, "msg": the text message exactly as on the wire}. Binary audio and waterfall frames and the
once-a-second "SET keepalive" are not recorded; the owner's address in "MSG client_public_ip" is masked.
"""

import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.parse
import wave
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
        if msg.startswith("MSG client_public_ip="):
            msg = "MSG client_public_ip=0.0.0.0"  # the owner's address: captures get committed
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

    import kiwi.client
    from kiwi.client import KiwiSDRStream

    host, port = args.receiver.rsplit(":", 1)
    ts = (1 << 62) | int(time.time() * 1_000_000)
    if args.browser_path:
        # Connect the way the KiwiSDR browser page does: take the connection timestamp the receiver
        # issues at /VER, and open /ws/no_wf/<ts>/<stream> ("no_wf": a page without a waterfall).
        # Some receivers close kiwiclient's own /<ts>/<stream> path right after auth.
        import urllib.request
        with urllib.request.urlopen(f"http://{host}:{port}/VER", timeout=10) as resp:
            ts = int(json.load(resp)["ts"])

        class BrowserPathHandshake(kiwi.client.ClientHandshakeProcessor):
            def handshake(self, resource):
                return super().handshake("/ws/no_wf" + resource)

        kiwi.client.ClientHandshakeProcessor = BrowserPathHandshake

    options = SimpleNamespace(
        server_host=host, server_port=int(port), wideband=False, socket_timeout=10,
        # Shared by both sockets: the server ties the EXT socket to the SND channel with the same
        # timestamp. Bit 62 is the server's NEW_TSTAMP_SPACE, which skips its client-IP match — needed
        # because a corporate gateway can send the two sockets out through different addresses.
        ws_timestamp=ts,
        nolocal=False, admin=False, password="", tlimit_password="",
        # The receiver treats the CW-mode frequency as the signal's own and shifts the tone itself, so
        # no passband-centre correction: kiwiclient's --pbc moved signals ~500 Hz, out of the passband.
        freq_pbc=False, tlimit=None, stats=False, idx=0, wf_cal=None,
        # read by kiwiclient's audio and waterfall paths, which this spike bypasses
        netcat=False, sound=False, resample=0, S_meter=-1, sdt=0, tstamp=False, station=None,
        filename="", dir=None, test_mode=False, rev_bin=False, nb=False, nb_test=False,
        multiple_connections=False, camp_allow_1ch=False, bad_cmd=False, ADC_OV=False,
        modulation="cw", lp_cut=args.passband_hz[0], hp_cut=args.passband_hz[1], user=IDENTITY,
    )
    channel = {}  # the SND channel number, when the receiver announces it

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
            if tag in ("MSG", "EXT"):  # text frames; audio and waterfall frames are binary
                capture.write(self._type, "←", bytes(message).decode("utf-8", "replace"))
            super()._process_ws_message(message)

        def _process_aud(self, body):
            # The audio itself is not needed (the receiver decodes the CW); only its signal level.
            self.frames = getattr(self, "frames", 0) + 1
            if len(body) >= 7:
                self.rssi = 0.1 * int.from_bytes(bytes(body[5:7]), "big") - 127
            now = time.time()
            if now - getattr(self, "_last_report", 0) >= 10:
                self._last_report = now
                print(f"\n[audio frames {self.frames} · signal {getattr(self, 'rssi', float('nan')):.1f} dBm]",
                      file=sys.stderr, flush=True)

        def _process_wf(self, body):
            pass

    class Sound(Stream):
        def __init__(self):
            super().__init__("SND")
            self.wav = None  # set by listen() when --audio is given

        def _process_aud(self, body):
            super()._process_aud(body)
            if self.wav is None or len(body) <= 7:
                return
            import numpy as np

            flags, data = body[0], bytes(body[7:])
            if flags & 0x10:  # SND_FLAG_COMPRESSED: IMA ADPCM, kiwiclient decodes it
                samples = np.asarray(self._decoder.decode(data), dtype=np.int16)
            else:
                samples = np.frombuffer(data, dtype=">i2")
            self.wav.writeframes(samples.astype("<i2").tobytes())

        def _process_msg_param(self, name, value):
            if name == "rx_chan" and value is not None:
                channel["rx"] = value
            super()._process_msg_param(name, value)

        def open(self):
            super().open()
            if args.browser_path:  # the page greets and tunes right after auth, without waiting
                self._send_message(f"SERVER DE CLIENT {IDENTITY} SND")
                self._setup_rx_params()

        def _setup_rx_params(self):
            if getattr(self, "_tuned", False):
                return
            self._tuned = True
            self.set_name(IDENTITY)
            self.set_mod("cw", args.passband_hz[0], args.passband_hz[1], args.freq)
            self.set_agc(on=True)
            if args.audio:
                self._set_snd_comp(False)  # plain 16-bit samples for the recording

    class Decoder(Stream):
        def __init__(self):
            super().__init__("EXT")
            # The decoder socket is silent until there is a signal to decode; a short read timeout
            # would end the session in the first quiet stretch.
            self._options = SimpleNamespace(**{**vars(options), "socket_timeout": 600})

        def _setup_rx_params(self):
            # After "EXT ready" the commands follow the browser order: start, tone offset, speed, threshold,
            # which must follow cw_wpm because setting the speed re-initialises the decoder.
            if getattr(self, "_switched", False):
                return
            self._switched = True
            self.set_name(IDENTITY)
            # The receiver ignores rx_chan here (v1.902 ext.cpp): it attaches the decoder to the channel
            # tied to this socket by the shared timestamp, so the decoder can only ever hear our channel.
            self._send_message(f"SET ext_switch_to_client=CW_decoder first_time=1 rx_chan={channel.get('rx', 0)}")
            # The receiver flushes this socket's input on the switch (EXT-STOP-FLUSH-INPUT) and answers
            # "EXT ready"; the decoder commands go only after that, as the browser does.

        def _start_decoder(self):
            if getattr(self, "_started", False):
                return
            self._started = True
            self._send_message(f"SET cw_start={TRAINING}")
            self._send_message(f"SET cw_pboff={args.pboff}")
            self._send_message(f"SET cw_wpm=0,{TRAINING}")
            self._send_message("SET cw_auto_thresh=0")
            self._send_message(f"SET cw_threshold={round(10 ** (THRESHOLD_DB / 10))}")
            if args.decoder_test:  # the receiver plays its own recorded CW through the decoder
                self._send_message("SET cw_test=1")

        def _process_ext(self, name, value):
            if name == "ready":
                self._start_decoder()
            elif name == "cw_chars" and value is not None:
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
    audio = pathlib.Path(args.audio) if args.audio else None
    if audio:
        audio.parent.mkdir(parents=True, exist_ok=True)
        sound.wav = wave.open(str(audio), "wb")  # noqa: SIM115 - open for the whole session, closed below
        sound.wav.setnchannels(1)
        sound.wav.setsampwidth(2)
        sound.wav.setframerate(12000)  # the KiwiSDR audio rate
    print(f"{args.receiver} · {args.freq} kHz"
          f"{' · capture ' + str(out) if out else ''}{' · audio ' + str(audio) if audio else ''}"
          " — Ctrl-C to stop", file=sys.stderr)

    streams = [sound] + ([decoder] if args.kiwi_decoder else [])
    for i, s in enumerate(streams):
        if i:
            time.sleep(2)  # the channel must exist before the extension attaches to it
        threading.Thread(target=drive, args=(s, stop, errors), daemon=True).start()
    try:
        while not stop.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    if args.kiwi_decoder:
        decoder.stop_decoder()
    stop.set()
    for s in reversed(streams):
        try:
            s.close()
        except Exception:  # noqa: BLE001, S110 - best effort on the way out
            pass
    capture.close()
    print(file=sys.stderr)
    for err in errors:
        print(f"receiver ended the session — {err}", file=sys.stderr)
    if audio:
        sound.wav.close()
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import cw_decode

        x, fs = cw_decode.load_wav(str(audio))
        if len(x) == 0:
            print("no audio was recorded", file=sys.stderr)
            return 1
        r = cw_decode.decode_audio(x, fs, args.passband_hz)
        print("--- decoded on the Mac (poc/receiver/cw_decode.py) ---", file=sys.stderr)
        print(r["text"] or "(no CW found)")
        print(f"[{r['seconds']:.0f} s · tone {r['tone_hz']:.0f} Hz, {r['prominence_db']:.1f} dB above the passband"
              f" · ~{r['wpm']:.0f} WPM]", file=sys.stderr)
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--receiver", help="host:port of a public KiwiSDR")
    ap.add_argument("--freq", type=float, help="the signal's frequency in kHz; it lands on a ~500 Hz tone")
    ap.add_argument("--passband", default=f"{CW_PASSBAND[0]}-{CW_PASSBAND[1]}",
                    help="audio passband in Hz (default %(default)s); wider, e.g. 200-2800, tolerates a frequency"
                         " read off the waterfall")
    ap.add_argument("--pboff", type=int, default=500, help="tone offset for --kiwi-decoder, Hz (default 500)")
    ap.add_argument("--out", help="write the raw capture to this JSONL file")
    ap.add_argument("--replay", help="print the text of a saved capture and exit (offline)")
    ap.add_argument("--audio", help="record the channel audio to this WAV file and decode it on the Mac")
    ap.add_argument("--kiwi-decoder", action="store_true",
                    help="also attach the receiver's own CW_decoder extension (EXT socket)")
    ap.add_argument("--decoder-test", action="store_true",
                    help="diagnostic: have the receiver play its built-in CW test file through the decoder")
    ap.add_argument("--browser-path", action="store_true",
                    help="connect like the browser page: the /VER timestamp and the /ws/no_wf/ path")
    args = ap.parse_args()
    args.passband_hz = tuple(int(v) for v in args.passband.split("-"))
    if args.replay:
        return replay(pathlib.Path(args.replay))
    if not args.receiver or args.freq is None:
        ap.error("--receiver and --freq are required to listen (or use --replay)")
    return listen(args)


if __name__ == "__main__":
    sys.exit(main())
