# Roadmap — sruti

Four self-contained versions, built in order: **v0** groundwork (text from the receiver, the piece model proven) → **v1** the listening agent (receiver link, pieces and sessions, piece explainer, the desktop app, session explainer) → **v2** decoding on the Mac → **v3** finding traffic. Versions are numbered from 0; phases inside a version are numbered `vA.B` (A = version, B = phase), e.g. `v1.3`. Each phase lists a **Goal**, a short description, a **Tasks** list, and a **Definition of Done (DoD)**, and ships with the automated tests that encode its DoD (see [ARCHITECTURE.md](ARCHITECTURE.md) §Testing).

Arc of the two axes: capabilities grow decoded text → pieces and saved, named sessions → a word-by-word gloss and a message per piece (Gemini 3.8 Flash) → the whole-session explanation on demand (Claude Opus 5.5) → a second text source decoded on the Mac → choosing where to listen; the interface grows headless CLI (v1.1) → the desktop window (v1.4). The **core is built first and never depends on the interface**. Complexity is added only by version, never all at once.

**Versioning (`A.B.C`).** `A` = roadmap version (v0→0 … v3→3), `B` = phase within it (`v1.3` → `1.3.0`), `C` = a post-release fix on that phase. Roadmap phase `vA.B` → semver `A.B.0`; a fix after it bumps `C`. Releases are cut per phase. Never bump the version without explicit confirmation.

---

## v0 — Groundwork: text from the receiver, the piece model proven

Remove the two unknowns everything else rests on — **whether the receiver's decoder delivers usable text**, and **whether the piece model explains it well enough** — before any product code is written. Both phases are spikes and measurements, not product code: v0.1 exercises the KiwiSDR protocol end to end (it is read from the KiwiSDR source but has never run) and records the sessions every later test replays; v0.2 turns the model comparison in [poc/RESULTS.md](../poc/RESULTS.md) into a measured baseline on golden examples. Depends on: nothing — this is the foundation.

### v0.1 — Text from the receiver

**Goal:** decoded CW text from a public KiwiSDR arrives on the Mac.

A spike on `kiwiclient`: open an audio channel in CW mode on a public KiwiSDR, attach the receiver's `CW_decoder` extension and print the `cw_chars` it sends (ARCHITECTURE §The receiver). Two things are settled here before anything depends on them: the **tone offset** — with `--pbc` the beacon on exactly 14.100 MHz came out as a ~1003 Hz tone, not the expected 500 Hz, and the decoder only hears the tone at `cw_pboff` — and **`kiwiclient`'s license**, since the checkout has none. The recordings become the fixtures for the fake receiver and the material for golden examples; the extension messages observed become the capture inspector's vocabulary (v1.4).

**Tasks:**
- **The spike:** an audio channel in CW mode plus the `CW_decoder` extension, printing `cw_chars`.
- **The tone offset:** why a 14.100 MHz carrier came out at ~1003 Hz, and which `cw_pboff` matches the passband.
- **Receivers:** pick three public receivers with good HF reception and free slots.
- **License:** check `kiwiclient`'s license before depending on it (the checkout has no license file).
- **Recordings:** record three sessions to JSONL — the beacons, a CQ run, a conversation.
- **Message inventory:** note every extension message type seen and how it parses — the raw material for the config panel's capture inspector (v1.4).

**DoD:** on 14.100 MHz the beacon call signs (e.g. `OH2B`) appear as text; a live conversation in 7.000–7.040 or 14.000–14.070 MHz produces readable text; the recordings are saved.

**Tests:** none automated — a spike. Its recordings become fixtures.

### v0.2 — Prove the piece model

**Goal:** Gemini 3.8 Flash reaches the bar on the golden examples inside the 5 s budget, with the prompt and the glossary form settled.

Sections 2–3 run on **Gemini 3.8 Flash**; the PoC comparison behind that choice (local models, Gemini 2.5 Flash, 3.1 Pro, 3.8 Flash — latency, quality, price) is in [poc/RESULTS.md](../poc/RESULTS.md). This phase replaces the PoC's single example with golden examples and settles what the PoC left open: the **glossary form** in the prompt — the full glossary (`glossary/cw.md`) or the short hints file (`glossary/cw-hints.md`) — and the prompt itself, including the three actions `none`, `append` and `rebuild`. The bar is example 001's reference answer. Depends on: v0.1 (the recordings).

**Tasks:**
- **Golden examples:** turn example 001 and the v0.1 recordings into golden examples — raw text plus a reference word-by-word gloss and English message translation, and a reference Ukrainian explanation from the session tier.
- **The run:** run `gemini-3.8-flash` with the `{gloss, action, message/rebuilt}` schema over the golden examples; record quality notes, latency and cost per piece.
- **The glossary form:** settle it for the prompt — the full glossary or the short hints file.

**DoD:** on the golden examples the model reaches the bar inside the budget; the prompt and the glossary form are written into ARCHITECTURE.

**Tests:** the golden-example eval script, opt-in.

---

## v1 — The listening agent: receiver link, pieces and sessions, piece explainer, the desktop app, session explainer

The product, built from the core outward. v1.1 stands up the project and the **receiver link**, with a headless CLI that prints the character stream. v1.2 cuts the stream into **pieces** and saves everything as **sessions** that can be named, switched and reopened. v1.3 adds the **piece explainer** (sections 2–3, Gemini 3.8 Flash). v1.4 puts it all in the **desktop window** — the four sections, the config panel with the capture inspector, the session switcher. v1.5 fills section 4 with the **session explainer** (Claude Opus 5.5, only on the Explain press). The core never imports the app: the window is a shell over the core's events and commands, talking through the pywebview bridge with no port (ARCHITECTURE §Core and the desktop app). Depends on: v0 (the recordings that become fixtures, the tone offset, the prompt and glossary form).

### v1.1 — Project skeleton and the receiver link

**Goal:** `sruti listen --receiver <host:port> --freq <kHz>` streams decoded text to the terminal (headless; the app window comes in v1.4).

The Python project, its configuration and the **receiver link** — sruti's own WebSocket client for the SND and EXT sockets, written from the protocol the v0.1 captures show (`kiwiclient` has no license and stays out of the product): it opens the audio channel, attaches the `CW_decoder` extension with the `cw_pboff` settled in v0.1, and emits decoded characters with timestamps, decoder status (speed, training), link states and the **raw extension messages** as events on the core event stream. It reconnects with backoff; "receiver busy" and "time limit reached" are states, not crashes. Listen only, and a polite guest: one connection per run, identified as `sruti`, nothing sent beyond the documented tuning and decoder `SET` messages. Depends on: v0.1.

**Tasks:**
- **The project:** Python with `uv`, ruff, pytest and CI.
- **Configuration:** the config file (`sruti.toml`) and `.env`.
- **The receiver link:** the `receiver` module — sruti's own client for the SND and EXT sockets — emitting characters, decoder status and the raw extension messages as events.
- **Robustness:** reconnect with backoff; busy and time-limit states.

**DoD:** an hour of listening survives a dropped connection; the raw capture replays to the same text.

**Tests:** unit — `cw_chars` decoding, link states; integration — the fake receiver replays a recorded session.

### v1.2 — Pieces and the session store

**Goal:** the character stream is cut into pieces, and everything is saved as sessions that can be reopened.

The pure **segmenter** closes a piece on an end-of-turn prosign standing alone, on 3 s of silence or at 200 characters; the piece is the piece tier's buffer. **Sessions are manual**: on launch sruti connects with the `sruti.toml` defaults and that opens the first one; retuning closes it and opens the next; `SK` and silence close pieces, never sessions. The **store** writes one append-only JSONL file per session in the record shapes of ARCHITECTURE §Pieces and sessions, and replays a saved session into the same event stream, read-only. Depends on: v1.1.

**Tasks:**
- **The segmenter:** pure characters → pieces; thresholds in configuration, tuned on the v0.1 recordings.
- **The store:** one append-only JSONL file per session under `var/sessions/` with the records from ARCHITECTURE.md, starting with the `session` header (auto name from date · receiver · frequency; rename appends a new header, latest wins).
- **Manual session boundaries:** a retune closes the session and opens a new one.
- **Replay:** a saved session replays into the event stream.

**DoD:** on the recorded conversation, pieces end where the operators hand over; a saved session replays identically; retuning starts a new session file; a rename survives reopening and never touches the file name.

**Tests:** unit — every piece rule, timing edge cases, store round-trip and replay, naming and rename.

### v1.3 — Piece explainer

**Goal:** within 5 s of a piece closing, its word-by-word gloss and its English message translation (sections 2 and 3) exist.

One call per **closed piece**: instructions and glossary (the stable prefix) + the last raw pieces + the recent section-3 entries + the new piece → Gemini 3.8 Flash with a response schema → `{gloss, action, message/rebuilt}`. The gloss is the literal layer, every token covered; the message is the communicative layer — what was said, CW repeats collapsed, nothing invented; the action is `none` (a repeat, shown as a ×n counter), `append` (one new entry) or `rebuild` (a marked replacement of the recent entries the model was shown). Both sections are append-only on screen and the store stays append-only (ARCHITECTURE §The four sections). Depends on: v0.2 (the prompt and glossary form), v1.2 (pieces).

**Tasks:**
- **The glossary:** the `glossary/` data file in the form settled in v0.2.
- **Prompt assembly**, with the stable prefix first.
- **The Gemini API client:** structured output against the `{gloss, action, message/rebuilt}` schema, thinking level low, the key in the request header.
- **Buffering is the piece** — never word-by-word calls.
- **Cost:** the running cost summed per session.
- **Degrade:** on failure or without a Gemini key, raw text only.

**DoD:** on example 001 the model reaches the bar set in v0.2, inside the budget.

**Tests:** unit — prompt assembly, schema validation, error paths (mocked Gemini client); eval — golden examples, opt-in.

### v1.4 — The desktop app

**Goal:** `uv run sruti app` opens the four-section window — original text, word by word, message, what is going on — with the config panel and the session switcher.

A native macOS window from **pywebview** on the system WebKit. The page — one HTML file with inline CSS and JavaScript — is the **Claude Design deliverable** made against [design/BRIEF.md](design/BRIEF.md), handed to the window as a string, so no HTTP server starts. The **bridge** object exposes the core commands to the page, and Python pushes core events in with `evaluate_js` — no socket, no port, not even on loopback (ARCHITECTURE §Core and the desktop app). `poc/desktop/` is the working prototype for the Python side. Depends on: v1.2 (sessions to switch and replay), v1.3 (sections 2–3).

**Tasks:**
- **The window:** pywebview on the core event stream; the page as one inline HTML file handed to the window as a string.
- **The bridge:** the bridge object exposing the core commands to the page; core events pushed in with `evaluate_js`.
- **The four sections:** section 1 streams live, sections 2–3 fill as each piece closes, section 4 is the Explain pane (wired in v1.5, showing "Explain off" until then).
- **The header:** the session name (click to rename), receiver, frequency, link status and running costs.
- **The config panel:** receiver, frequency, `cw_pboff`, decoder parameters, languages — with the **capture inspector** showing the raw extension messages next to how each parsed, applied on reconnect.
- **The session switcher:** list saved sessions by name, open one as a read-only replay, start a new session by retuning, and **rename** the current or a past session in place.
- **The page:** the Claude Design deliverable made against `specification/design/BRIEF.md`; `poc/desktop/` is the working prototype for the Python side.

**DoD:** a recorded session replayed through the fake receiver fills sections 1–3 live in the window; the connection settings can be changed from the panel and the raw API traffic is visible; a past session can be opened, a new one started by retuning, and a session renamed from the app; no listening socket exists while the app runs.

**Tests:** unit — the bridge object driven over the fake receiver with a fake window recording every `evaluate_js` call (commands in, events out, in order); a test that the window is created from a string with no HTTP server; the page rendered from a recorded snapshot in a headless browser, opt-in.

### v1.5 — Session explainer

**Goal:** pressing **Explain** fills section 4 with a whole-session explanation in Ukrainian at the quality of the reference answer.

The **Explain** press sends the whole session — glossary and every piece so far — to Claude Opus 5.5 (Fable 5.1 by configuration) and renders the Ukrainian explanation in section 4, rebuilt wholesale on every press. Only on the press: never on a timer, at session end or on reconnect. While a call runs the button is disabled; a failed call keeps the previous explanation with an error note; without a Claude key section 4 reads "Explain off" and everything else works (ARCHITECTURE §The four sections). Depends on: v1.4 (the button), v1.2 (the session), v0.2 (the golden examples).

**Tasks:**
- **The Claude API client:** Opus 5.5 by default, Fable 5.1 by configuration.
- **The `explain` command**, wired from the app's Explain button to the call.
- **Prompt caching** on the stable prefix.
- **Cost:** per-call cost shown and summed per session.
- **Off without a key:** without a Claude key the button reports Explain is off.

**DoD:** on example 001 the output matches the reference answer in substance; without a Claude key everything except section 4 works, without errors; no call ever happens without a press.

**Tests:** unit — trigger handling, cost accounting, mocked client; eval — golden examples, opt-in.

---

## v2 — Decoding on the Mac (not yet phased)

A second text source, for receivers without the decoder extension or when its decoding is poor: audio from the same receiver channel → a local CW decoder (tone detection, adaptive timing) → the same character stream. Compared with the receiver's decoder on recorded audio; the source is selectable per run. Broken into phases once v1 is in use. Depends on: v1 (the receiver link and the character stream it feeds).

## v3 — Finding traffic (open)

The agent chooses where to listen. To be decided once v1 is in use: choose receivers from the public directory by band, load and reception; scan CW band segments on the receiver's waterfall for active signals; follow DX-cluster or Reverse Beacon Network spots; stay with a conversation while it lasts. Depends on: v1.

---

## Contract mapping

- **KiwiSDR extension messages** (ARCHITECTURE §The receiver) — exercised end to end in **v0.1**, implemented by the receiver link in **v1.1**, shown raw in the capture inspector in **v1.4**.
- **CLI** — `sruti listen --receiver <host:port> --freq <kHz>` in **v1.1**; `sruti app` in **v1.4**.
- **Segmenter rules and thresholds** (end-of-turn prosigns, pause, length cap; in configuration) — **v1.2**.
- **Record shapes and the session store layout** — `session`, `char`, `piece` and `var/sessions/<started>-<receiver>-<freq>.jsonl` in **v1.2**; `explanation` with `tier: "piece"` in **v1.3**; with `tier: "session"` in **v1.5**.
- **Core commands** (`tune`, `start`/`stop`, `open-session`, `rename-session`, `set-config`) — in the core from **v1.2**, exposed to the page through the bridge in **v1.4**; `explain` wired in **v1.5**.
- **Piece explainer schema** `{gloss, action, message/rebuilt}` and its three actions — the prompt settled in **v0.2**, the client in **v1.3**.
- **Four-section display contract** and the page's event and command names ([design/BRIEF.md](design/BRIEF.md) §8) — **v1.4**.
- **Two-tier table** — the piece tier in **v1.3**, the session tier in **v1.5**.

## Deferred

A call-sign prefix → country lookup from a maintained table (e.g. the CTY files), not from model memory; own SDR hardware on `ich-picobox`, behind the same receiver interface — beyond v0–v3.
