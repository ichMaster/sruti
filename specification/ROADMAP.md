# Roadmap — sruti

Versions are built in order; phases inside a version are numbered `vA.B`. Each phase has a **Goal**,
**Tasks**, a **Definition of Done (DoD)** and **Tests**.

v0 removes the two unknowns everything else rests on — whether the receiver's decoder delivers usable
text, and whether the piece model explains it well enough — before any product code is written. v1
delivers the listening agent as a four-section desktop app.

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

### v0.2 — Prove the piece model

**Goal:** Gemini 3.8 Flash reaches the bar on the golden examples inside the 5 s budget, with the prompt
and the glossary form settled.

**Tasks:**
- Turn example 001 and the v0.1 recordings into golden examples: raw text plus a reference word-by-word
  gloss and English message translation, and a reference Ukrainian explanation from the session tier.
- Run `gemini-3.8-flash` with the `{gloss, action, message/rebuilt}` schema over the golden examples;
  record quality notes, latency and cost per piece.
- Settle the glossary form for the prompt: the full glossary or the short hints file.

**DoD:** on the golden examples the model reaches the bar inside the budget; the prompt and the glossary
form are written into ARCHITECTURE.

**Tests:** the golden-example eval script, opt-in.

---

## v1 — The listening agent (desktop app)

### v1.1 — Project skeleton and the receiver link

**Goal:** `sruti listen --receiver <host:port> --freq <kHz>` streams decoded text to the terminal
(headless; the app window comes in v1.4).

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
from ARCHITECTURE.md, starting with the `session` header (auto name from date · receiver · frequency;
rename appends a new header, latest wins); manual session boundaries — a retune closes the session and
opens a new one; replay of a saved session into the event stream.

**DoD:** on the recorded conversation, pieces end where the operators hand over; a saved session replays
identically; retuning starts a new session file; a rename survives reopening and never touches the file
name.

**Tests:** unit — every piece rule, timing edge cases, store round-trip and replay, naming and rename.

### v1.3 — Piece explainer

**Goal:** within 5 s of a piece closing, its word-by-word gloss and its English message translation
(sections 2 and 3) exist.

**Tasks:** the `glossary/` data file in the form settled in v0.2; prompt assembly; the Gemini API client —
structured output against the `{gloss, action, message/rebuilt}` schema, thinking level low, the key in
the request header; buffering is the piece — never word-by-word calls; the running cost summed per
session; on failure or without a Gemini key, raw text only.

**DoD:** on example 001 the model reaches the bar set in v0.2, inside the budget.

**Tests:** unit — prompt assembly, schema validation, error paths (mocked Gemini client); eval — golden
examples, opt-in.

### v1.4 — The desktop app

**Goal:** `uv run sruti app` opens the four-section window — original text, word by word, message, what
is going on — with the config panel and the session switcher.

**Tasks:** the pywebview window on the core event stream; the page as one inline HTML file handed to the
window as a string; the bridge object exposing the core commands to the page, and core events pushed in
with `evaluate_js`; section 1 streams live, sections 2–3 fill as each piece closes, section 4 is the
Explain pane (wired in v1.5, showing "Explain off" until then); the header with the session name (click
to rename), receiver, frequency, link status and running costs; the config panel — receiver, frequency,
`cw_pboff`, decoder parameters, languages — with the **capture inspector** showing the raw extension
messages next to how each parsed, applied on reconnect; the session switcher — list saved sessions by
name, open one as a read-only replay, start a new session by retuning, and **rename** the current or a
past session in place. The page is the Claude Design deliverable made against
`specification/design/BRIEF.md`; `poc/desktop/` is the working prototype for the Python side.

**DoD:** a recorded session replayed through the fake receiver fills sections 1–3 live in the window; the
connection settings can be changed from the panel and the raw API traffic is visible; a past session can
be opened, a new one started by retuning, and a session renamed from the app; no listening socket exists
while the app runs.

**Tests:** unit — the bridge object driven over the fake receiver with a fake window recording every
`evaluate_js` call (commands in, events out, in order); a test that the window is created from a string
with no HTTP server; the page rendered from a recorded snapshot in a headless browser, opt-in.

### v1.5 — Session explainer

**Goal:** pressing **Explain** fills section 4 with a whole-session explanation in Ukrainian at the
quality of the reference answer.

**Tasks:** Claude API client (Opus 5.5 by default, Fable 5.1 by configuration); the `explain` command
wired from the app's Explain button to the call; prompt caching on the stable prefix; per-call cost shown and summed
per session; without a Claude key the button reports Explain is off.

**DoD:** on example 001 the output matches the reference answer in substance; without a Claude key
everything except section 4 works, without errors; no call ever happens without a press.

**Tests:** unit — trigger handling, cost accounting, mocked client; eval — golden examples, opt-in.

---

## v2 — Decoding on the Mac

**Goal:** a second text source, for receivers without the decoder extension or when its decoding is poor.

Audio from the same receiver channel → a local CW decoder (tone detection, adaptive timing) → the same
character stream. Compared with the receiver's decoder on recorded audio; the source is selectable per
run.

## v3 — Finding traffic (open)

**Goal:** the agent chooses where to listen.

To be decided once v1 is in use: choose receivers from the public directory by band, load and
reception; scan CW band segments on the receiver's waterfall for active signals; follow DX-cluster or
Reverse Beacon Network spots; stay with a conversation while it lasts.

## Later

- Call-sign prefix → country from a maintained table (e.g. the CTY files), not from model memory.
- Own SDR hardware on `ich-picobox`, behind the same receiver interface.
