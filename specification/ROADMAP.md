# Roadmap — sruti

Versions are built in order; phases inside a version are numbered `vA.B`. Each phase has a **Goal**,
**Tasks**, a **Definition of Done (DoD)** and **Tests**.

v0 removes the two unknowns everything else rests on — whether the receiver's decoder delivers usable
text, and whether a local model is good enough — before any product code is written. v1 delivers the
listening agent with the four-section TUI; v2 puts the same agent in the browser.

---

## v0 — Groundwork

### v0.1 — Text from the receiver

**Goal:** decoded CW text from a public KiwiSDR arrives on the Mac.

**Tasks:**
- A spike on `kiwiclient`: an audio channel in CW mode plus the `CW_decoder` extension, printing `cw_chars`.
- Resolve the tone offset: why a 14.100 MHz carrier came out at ~1003 Hz, and which `cw_pboff` matches the passband.
- Pick three public receivers with good HF reception and free slots.
- Check `kiwiclient`'s license before depending on it (the checkout has no license file).
- Record three sessions to JSONL: the beacons, a CQ run, a conversation.
- Note every extension message type seen and how it parses — the raw material for the config panel's
  capture inspector (v1.4).

**DoD:** on 14.100 MHz the beacon call signs (e.g. `OH2B`) appear as text; a live conversation in
7.000–7.040 or 14.000–14.070 MHz produces readable text; the recordings are saved.

**Tests:** none automated — a spike. Its recordings become fixtures.

### v0.2 — Choose the local model

**Goal:** a local model that is good and fast enough — or a recorded decision that none is.

**Tasks:**
- Turn example 001 and the v0.1 recordings into golden examples: raw text plus a reference word-by-word
  gloss and English message translation, and a reference Ukrainian explanation from the cloud tier.
- Run `gemma4:12b`, `qwen3.5:9b` and any newer candidate with the same prompt and the `{gloss, message}`
  schema; record quality notes and latency.
- For models that fail in one step, try two: restore the text in its own language, then gloss and
  translate.

**DoD:** a model is chosen with its measured latency per piece; or the local tier is cut down to what a
small model does well (e.g. glossary expansion only), and the decision is written into ARCHITECTURE.

**Tests:** the golden-example eval script, opt-in.

---

## v1 — The listening agent (TUI)

### v1.1 — Project skeleton and the receiver link

**Goal:** `sruti listen --receiver <host:port> --freq <kHz>` streams decoded text to the terminal
(headless; the TUI comes in v1.4).

**Tasks:** Python project (`uv`, ruff, pytest, CI); the config file (`sruti.toml`) and `.env`; the
`receiver` module on `kiwiclient`, emitting characters, decoder status and the raw extension messages as
events; reconnect with backoff; busy and time-limit states.

**DoD:** an hour of listening survives a dropped connection; the raw capture replays to the same text.

**Tests:** unit — `cw_chars` decoding, link states; integration — the fake receiver replays a recorded
session.

### v1.2 — Pieces and the session store

**Goal:** the character stream is cut into pieces, and everything is saved as sessions that can be
reopened.

**Tasks:** the pure `segmenter` (characters → pieces; thresholds in configuration, tuned on the v0.1
recordings); the `store` — one append-only JSONL file per session under `var/sessions/` with the records
from ARCHITECTURE.md; manual session boundaries — a retune closes the session and opens a new one; replay
of a saved session into the event stream.

**DoD:** on the recorded conversation, pieces end where the operators hand over; a saved session replays
identically; retuning starts a new session file.

**Tests:** unit — every piece rule, timing edge cases, store round-trip and replay.

### v1.3 — Local explainer

**Goal:** within 5 s of a piece closing, its word-by-word gloss and its English message translation
(sections 2 and 3) exist.

**Tasks:** the `glossary/` data file; prompt assembly; Ollama client with the `{gloss, message}` JSON
schema; buffering is the piece — never word-by-word calls; on failure, raw text only.

**DoD:** on example 001 the chosen model reaches the bar set in v0.2, inside the budget, on the Mac.

**Tests:** unit — prompt assembly, schema validation, error paths (mocked model); eval — golden examples,
opt-in.

### v1.4 — The TUI

**Goal:** the four-section terminal interface — original text, word by word, message, what is going on —
plus the config panel and the session switcher.

**Tasks:** the Textual app on the core event stream; section 1 streams live, sections 2–3 fill as each
piece closes, section 4 is the Explain pane (wired in v1.5, showing "cloud tier off" until then); the
config panel — receiver, frequency, `cw_pboff`, decoder parameters, languages — with the **capture
inspector** showing the raw extension messages next to how each parsed, applied on reconnect; the session
switcher — list saved sessions, open one as a read-only replay, start a new session by retuning.

**DoD:** a recorded session replayed through the fake receiver fills sections 1–3 live; the connection
settings can be changed from the panel and the raw API traffic is visible; a past session can be opened
and a new one started by retuning.

**Tests:** unit — the view models (pure presentation logic); the TUI driven headless (Textual pilot) over
the fake receiver.

### v1.5 — Cloud explainer

**Goal:** pressing **Explain** fills section 4 with a whole-session explanation in Ukrainian at the
quality of the reference answer.

**Tasks:** Claude API client (Opus 5.5 by default, Fable 5.1 by configuration); the `explain` command
wired from the TUI button to the call; prompt caching on the stable prefix; per-call cost shown and summed
per session; without an API key the button reports the cloud tier is off.

**DoD:** on example 001 the output matches the reference answer in substance; without an API key the
agent runs local-only, without errors; no call ever happens without a press.

**Tests:** unit — trigger handling, cost accounting, mocked client; eval — golden examples, opt-in.

---

## v2 — The web interface

The same agent in the browser. The core is untouched; only an interface is added, and the TUI remains.

### v2.1 — The local web server

**Goal:** the core's events and commands are reachable over HTTP on `127.0.0.1` only.

**Tasks:** the FastAPI app bound to `127.0.0.1`; the event stream over a WebSocket; the commands (tune,
start/stop, explain, open-session, set-config) as POSTs; serving the static page; `sruti web` next to
`sruti tui`.

**DoD:** the event stream and every command work over localhost; nothing listens on any LAN interface (a
test pins the binding).

**Tests:** unit — route handlers against a faked core; the localhost-only binding pinned.

### v2.2 — The browser UI

**Goal:** the four sections, the config panel with the capture inspector, and the session switcher in the
browser, at parity with the TUI.

**Tasks:** one static page, no build step; render the WebSocket stream into the four sections; the
Explain button; the config and session views.

**DoD:** a replayed session fills the sections in the browser; config edits and session switching work;
the TUI still passes its own DoD.

**Tests:** the page's view logic unit-tested; an end-to-end replay against the local server.

---

## v3 — Decoding on the Mac

**Goal:** a second text source, for receivers without the decoder extension or when its decoding is poor.

Audio from the same receiver channel → a local CW decoder (tone detection, adaptive timing) → the same
character stream. Compared with the receiver's decoder on recorded audio; the source is selectable per
run.

## v4 — Finding traffic (open)

**Goal:** the agent chooses where to listen.

To be decided once v1 and v2 are in use: choose receivers from the public directory by band, load and
reception; scan CW band segments on the receiver's waterfall for active signals; follow DX-cluster or
Reverse Beacon Network spots; stay with a conversation while it lasts.

## Later

- Call-sign prefix → country from a maintained table (e.g. the CTY files), not from model memory.
- Own SDR hardware on `ich-picobox`, behind the same receiver interface.
