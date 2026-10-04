#!/usr/bin/env python3
"""Desktop PoC: the four-section sruti window in pywebview.

A fake receiver replays example 001 character by character, the way the KiwiSDR CW decoder would
send it. Each closed piece gets the gloss and message recorded from gemini-3.8-flash (or, with
--live, a real Gemini call). Explain shows example 001's reference answer after a pause; Opus is
not called.

No port is opened: the page is handed to the window as a string, and Python and the page talk
through pywebview's JS bridge (window.pywebview.api -> Python, evaluate_js -> page).

Run:
    uv run --no-project --with pywebview python poc/desktop/app.py
    uv run --no-project --with pywebview python poc/desktop/app.py --live --speed 2
"""

import argparse
import dataclasses
import datetime
import json
import pathlib
import queue
import sys
import threading
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import explain_piece as ep

WPM = 22
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_PRICE = (0.75e-6, 3.75e-6)  # $ per input / output token, through 2026-12-31

# gemini-3.8-flash with glossary/cw-hints.md, recorded 2026-10-02 (poc/RESULTS.md).
RECORDED = [
    {
        "latency_ms": 2100, "cost_usd": 0.00175, "action": "append",
        "message": "[...] I am also changing transceiver and turning on the IC-7300",
        "gloss": [
            ["T E TTEAEANDE", "[damaged text]"], ["CAMBIO", "change"], ["ANCHE", "also"],
            ["IL", "the"], ["RTX", "transceiver"], ["ET", "and"], ["ACCENDO", "turn on"],
            ["L'", "the"], ["IC 7300", "IC-7300 (radio)"],
        ],
    },
    {
        "latency_ms": 3500, "cost_usd": 0.00327, "action": "append",
        "message": "Now I pass the turn back to you, IU3FEJ (?) from IZ4PHG, how copy? Over. Roger QSO "
                   "from IU2PEJ, thanks for the info. Maybe you don't know that it hasn't been long "
                   "that [...]",
        "gloss": [
            ["ALESORA", "allora (now/then, reconstructed)"], ["TI", "to you"],
            ["RIP", "ripasso (split: pass back)"], ["ASS", "[part of ripasso]"],
            ["O", "[part of ripasso]"], ["IL", "the"], ["CAMB", "cambio (split: over/turn)"],
            ["IO", "[part of cambio]"], ["IU3", "IU3"], ["F", "F"], ["E", "E"],
            ["JDE", "J (IU3FEJ (?)) de (from)"], ["IZ4PHG", "IZ4PHG"], ["HW", "how copy?"],
            ["K", "over"], ["R", "roger"], ["QSO", "contact"], ["DE", "from"],
            ["IU2PEJ", "IU2PEJ"], ["GRAZIE", "thanks"], ["PER", "for"], ["LE", "the"],
            ["INFTA", "info (?)"], ["EIO", "io (and I / I (?))"],
            ["ORSE", "forse (maybe, missing F)"], ["NON", "not"],
            ["UAI", "sai (you know, U/S error (?))"], ["CFE", "che (that, F/H error (?))"],
            ["NON", "not"], ["[err]T", "è (is / [err])"],
            ["ANTO", "tanto (much / long, reconstructed)"], ["CH", "che (that, incomplete)"],
        ],
    },
    {
        "latency_ms": 3300, "cost_usd": 0.00368, "action": "append",
        "message": "[... that] I have been doing CW, but my teacher is Lino. About 7 years ago I met "
                   "the great Lino and he took me under his wing and for [...]",
        "gloss": [
            ["E", "and"], ["FACCIO", "I do"], ["CW", "CW"], ["MA", "but"], ["IL", "the"],
            ["MIO", "my"], ["MAESTRO", "teacher / master"],
            ["[err]L", "is (È, damaged accented letter) / the"],
            ["INO", "Lino (split/reconstructed)"], ["CIRCA", "about"], ["7", "7"],
            ["ANNI", "years"], ["HO", "I"],
            ["COMOS[err]IUNO", "met / known (reconstruction: conosciuto)"], ["IL", "the"],
            ["GRANDE", "great"], ["LINO", "Lino"], ["ET", "and"], ["LUI", "he"], ["MI", "me"],
            ["HA", "has"], ["PRESO", "taken"], ["SOT T O", "under (sotto)"], ["LA", "the"],
            ["SUA", "his"], ["AAEA", "wing (reconstruction: ala)"], ["ET", "and"],
            ["PE R", "for (per)"],
        ],
    },
]


def reference_answer() -> list[str]:
    """Example 001's reference answer, as paragraphs."""
    text = (ROOT / "specification" / "examples" / "001-italian-ragchew.md").read_text(encoding="utf-8")
    section = text.split("## Reference answer", 1)[1].split("\n## ", 1)[0]
    paras: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        if not line.startswith(">"):
            continue
        body = line
        while body.startswith(">"):
            body = body[1:].strip()
        if body:
            current.append(body)
        elif current:
            paras.append(" ".join(current))
            current = []
    if current:
        paras.append(" ".join(current))
    return paras


def chars(text: str):
    """The decoder's units: single characters, with the [err] marker kept whole."""
    i = 0
    while i < len(text):
        if text.startswith("[err]", i):
            yield "[err]"
            i += 5
        else:
            yield text[i]
            i += 1


@dataclasses.dataclass
class Session:
    id: str
    name: str
    receiver: str
    freq_khz: float
    started: str
    events: list = dataclasses.field(default_factory=list)
    pieces: int = 0

    def summary(self) -> dict:
        return {"id": self.id, "name": self.name, "receiver": self.receiver,
                "freq_khz": self.freq_khz, "started": self.started, "pieces": self.pieces}


class Api:
    """Everything public here is callable from the page as window.pywebview.api.<name>()."""

    def __init__(self, live: bool, speed: float, selftest: float = 0.0, sink=None):
        self._window = None
        self._live = live
        self._speed = speed
        self._selftest = selftest
        self._sink = sink
        self._instant = sink is not None
        self._sessions: list[Session] = []
        self._current: Session | None = None
        self._stop = threading.Event()
        self._explaining = threading.Lock()
        self._lock = threading.Lock()
        self._acks = 0
        self._emitted = 0
        self._config = {
            "receiver": "replay:example-001",
            "freq_khz": 7020,
            "cw_pboff": 500,
            "training": 100,
            "wpm": 0,
            "threshold": "fixed, 47 dB",
            "word_space_correction": True,
            "language_piece": "en",
            "language_session": "uk",
            "piece_pause_s": 3,
            "piece_max_chars": 200,
            "piece_model": GEMINI_MODEL,
            "session_model": "claude-opus-5-5",
        }

    # ---------------------------------------------------------------- called from the page

    def ready(self) -> dict:
        if self._current is None:
            self._start_session(self._config["freq_khz"], self._config["receiver"])
        return {"config": self._config, "sessions": self.list_sessions(), "live": self._live,
                "selftest": bool(self._selftest), "current": self._current.summary()}

    def tune(self, freq_khz, receiver=None) -> dict:
        freq = float(freq_khz)
        return self._start_session(freq, receiver or self._current.receiver).summary()

    def list_sessions(self) -> list:
        with self._lock:
            return [s.summary() for s in reversed(self._sessions)]

    def session_events(self, session_id: str) -> list:
        with self._lock:
            session = self._find(session_id)
            return list(session.events) if session else []

    def rename_session(self, session_id: str, name: str) -> dict:
        name = (name or "").strip()
        with self._lock:
            session = self._find(session_id)
            if not session or not name:
                return {"ok": False}
            session.name = name
        self._emit({"type": "session", **session.summary(), "renamed": True})
        return {"ok": True, "session": session.summary()}

    def get_config(self) -> dict:
        return self._config

    def set_config(self, config: dict) -> dict:
        known = {k: v for k, v in (config or {}).items() if k in self._config}
        self._config.update(known)
        return {"ok": True, "config": self._config, "note": "Saved. Applied on the next tune."}

    def explain(self) -> dict:
        if not self._explaining.acquire(blocking=False):
            return {"ok": False, "reason": "busy"}
        session = self._current
        threading.Thread(target=self._run_explain, args=(session,), daemon=True).start()
        return {"ok": True}

    def ack(self, rendered: int) -> None:
        self._acks = max(self._acks, int(rendered))

    # ---------------------------------------------------------------- internals

    def _find(self, session_id: str) -> Session | None:
        return next((s for s in self._sessions if s.id == session_id), None)

    def _sleep(self, seconds: float) -> None:
        if not self._instant:
            time.sleep(seconds)

    def _emit(self, ev: dict, store: bool = True) -> None:
        session = self._current
        if session is not None:
            ev.setdefault("session", session.id)
            if store and ev["type"] in ("session", "char", "piece", "explanation", "lull", "end"):
                target = self._find(ev["session"]) or session
                with self._lock:
                    target.events.append(ev)
        self._emitted += 1
        if self._sink is not None:
            self._sink(ev)
        elif self._window is not None:
            self._window.evaluate_js(f"window.sruti && window.sruti.onEvent({json.dumps(ev)})")

    def _start_session(self, freq_khz: float, receiver: str) -> Session:
        self._stop.set()
        self._stop = threading.Event()
        now = datetime.datetime.now(datetime.timezone.utc).astimezone()
        freq_label = f"{freq_khz:g}"
        session = Session(
            id=f"{now:%Y%m%dT%H%M%S}-{len(self._sessions) + 1}",
            name=f"{now:%Y-%m-%d %H:%M} · {receiver} · {freq_label} kHz",
            receiver=receiver, freq_khz=freq_khz, started=now.isoformat(timespec="seconds"),
        )
        with self._lock:
            self._sessions.append(session)
            self._current = session
        self._emit({"type": "session", **session.summary()})
        if self._instant:
            self._replay(session, self._stop)
        else:
            threading.Thread(target=self._replay, args=(session, self._stop), daemon=True).start()
        return session

    def _raw(self, direction: str, msg: str, parsed: str) -> None:
        self._emit({"type": "raw", "dir": direction, "msg": msg, "parsed": parsed,
                    "t": time.strftime("%H:%M:%S")}, store=False)

    def _replay(self, session: Session, stop: threading.Event) -> None:
        cfg = self._config
        self._sleep(0.4)
        for msg, parsed in (
            ("SET ext_switch_to_client=CW_decoder first_time=1 rx_chan=0", "attach the CW decoder"),
            (f"SET cw_pboff={cfg['cw_pboff']}", f"listen on a {cfg['cw_pboff']} Hz tone"),
            (f"SET cw_wpm={cfg['wpm']},{cfg['training']}", "speed: automatic"),
            (f"SET cw_start={cfg['training']}", "start decoding"),
        ):
            self._raw("→", msg, parsed)
        for progress in (25, 50, 75, 100):
            if stop.is_set():
                return
            self._sleep(0.25)
            self._raw("←", f"cw_train={progress}", f"training {progress}")
        self._raw("←", f"cw_wpm={WPM}", f"speed {WPM} WPM")
        self._emit({"type": "status", "state": "listening", "wpm": WPM}, store=False)

        jobs: queue.Queue = queue.Queue()
        worker = None
        if not self._instant:
            worker = threading.Thread(target=self._piece_worker, args=(session, jobs), daemon=True)
            worker.start()
        state = {"context": [], "section3": []}

        per_char = 60 / (WPM * 5) / self._speed
        for seq, block in enumerate(ep.PIECES, 1):
            text = " ".join(block.split())
            t_start = time.time()
            for unit in chars(text):
                if stop.is_set():
                    jobs.put(None)
                    return
                self._raw("←", "cw_chars=" + urllib.parse.quote(unit), f"character {unit!r}")
                self._emit({"type": "char", "ch": unit, "t": time.time()})
                self._sleep(per_char)
            self._emit({"type": "status", "state": "lull", "wpm": WPM}, store=False)
            self._sleep(cfg["piece_pause_s"] / self._speed)
            session.pieces = seq
            piece = {"type": "piece", "seq": seq, "raw": text, "cut": "pause",
                     "receiver": session.receiver, "freq_khz": session.freq_khz, "wpm": WPM,
                     "t_start": t_start, "t_end": time.time()}
            self._emit(piece)
            self._emit({"type": "lull"})
            if self._instant:
                self._explain_piece(session, state, seq, text)
            else:
                jobs.put((seq, text))
            self._emit({"type": "status", "state": "listening", "wpm": WPM}, store=False)
            self._raw("←", f"cw_wpm={WPM}", f"speed {WPM} WPM")

        jobs.put(None)
        if worker is not None:
            worker.join()
        if stop.is_set():
            return
        self._emit({"type": "end"})
        self._emit({"type": "status", "state": "ended", "wpm": WPM}, store=False)
        if self._selftest and not self._instant:
            self.explain()

    def _piece_worker(self, session: Session, jobs: queue.Queue) -> None:
        state = {"context": [], "section3": []}
        while (job := jobs.get()) is not None:
            self._explain_piece(session, state, *job)

    def _explain_piece(self, session: Session, state: dict, seq: int, text: str) -> None:
        try:
            if self._live:
                system = ep.build_system("hints")
                user = ep.build_user(state["context"][-5:], state["section3"], text)
                answer, seconds, stats = ep.call(GEMINI_MODEL, system, user, timeout=30)
                cost = (stats["prompt_tokens"] * GEMINI_PRICE[0]
                        + (stats["out_tokens"] + stats["thought_tokens"]) * GEMINI_PRICE[1])
                result = {"action": answer.get("action", "append"), "gloss":
                          [[g.get("token", "?"), g.get("meaning", "?")] for g in answer.get("gloss") or []],
                          "message": answer.get("message"), "rebuilt": answer.get("rebuilt"),
                          "latency_ms": round(seconds * 1000), "cost_usd": round(cost, 5)}
            else:
                result = dict(RECORDED[(seq - 1) % len(RECORDED)])
                self._sleep(result["latency_ms"] / 1000)
        except Exception as exc:  # noqa: BLE001 - the piece degrades to raw text only
            self._emit({"type": "explanation", "tier": "piece", "piece_seq": seq,
                        "error": type(exc).__name__}, )
            return
        if result["action"] == "append" and result.get("message"):
            state["section3"].append(result["message"])
        elif result["action"] == "rebuild" and result.get("rebuilt"):
            state["section3"] = list(result["rebuilt"])
        state["context"].append(text)
        self._emit({"type": "explanation", "tier": "piece", "piece_seq": seq,
                    "model": GEMINI_MODEL, "recorded": not self._live, **result})

    def _run_explain(self, session: Session) -> None:
        try:
            self._emit({"type": "explain_state", "state": "running", "session": session.id}, store=False)
            started = time.time()
            self._sleep(2.5)
            self._emit({"type": "explanation", "tier": "session", "session": session.id,
                        "upto_seq": session.pieces, "model": "claude-opus-5-5",
                        "paragraphs": reference_answer(), "simulated": True,
                        "latency_ms": round((time.time() - started) * 1000), "cost_usd": 0.03})
        finally:
            self._emit({"type": "explain_state", "state": "idle", "session": session.id}, store=False)
            self._explaining.release()


def page() -> str:
    return (HERE / "index.html").read_text(encoding="utf-8")


def write_preview(path: pathlib.Path) -> None:
    """A static copy of the page with a whole recorded session baked in, for a browser screenshot."""
    events: list = []
    api = Api(live=False, speed=1, sink=events.append)
    init = api.ready()
    api._explaining.acquire()
    api._run_explain(api._current)
    snapshot = {"init": init, "events": events}
    html = page().replace("<!--PREVIEW-->", f"<script>window.__PREVIEW__ = {json.dumps(snapshot)};</script>")
    path.write_text(html, encoding="utf-8")
    print(f"preview written: {path} ({len(events)} events)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="call gemini-3.8-flash for each piece (paid)")
    ap.add_argument("--speed", type=float, default=4.0, help="replay speed vs 22 WPM (default 4x)")
    ap.add_argument("--selftest", type=float, default=0.0, metavar="SECONDS",
                    help="run, press Explain at the end, close after SECONDS and print a summary")
    ap.add_argument("--preview", type=pathlib.Path, help="write a static preview page and exit")
    args = ap.parse_args()

    if args.preview:
        write_preview(args.preview)
        return 0

    import webview

    api = Api(live=args.live, speed=args.speed, selftest=args.selftest)
    window = webview.create_window("sruti", html=page(), js_api=api, width=1320, height=860,
                                   min_size=(980, 640), text_select=True, background_color="#11161c")
    api._window = window

    def selftest_timer():
        time.sleep(args.selftest)
        print(f"selftest: emitted={api._emitted} rendered_ack={api._acks} "
              f"sessions={len(api._sessions)} pieces={api._current.pieces}")
        window.destroy()

    webview.start(selftest_timer if args.selftest else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
