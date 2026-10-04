# Roadmap — sruti

Three self-contained versions, built in order: **v0** groundwork (text from the receiver's audio, decoded on the Mac; the piece model proven) → **v1** the listening agent (receiver link, CW decoder, pieces and sessions, piece explainer, the desktop app, session explainer) → **v2** finding traffic. Versions are numbered from 0; phases inside a version are numbered `vA.B` (A = version, B = phase), e.g. `v1.3`. Each phase lists a **Goal**, a short description, a **Tasks** list, and a **Definition of Done (DoD)**, and ships with the automated tests that encode its DoD (see [ARCHITECTURE.md](ARCHITECTURE.md) §Testing).

Arc of the two axes: capabilities grow receiver audio → characters decoded on the Mac → pieces and saved, named sessions → a word-by-word gloss and a message per piece (Gemini 3.8 Flash) → the whole-session explanation on demand (Claude Opus 5.5) → choosing where to listen; the interface grows headless CLI (v1.1) → the desktop window (v1.5). The **core is built first and never depends on the interface**. Complexity is added only by version, never all at once.

**Versioning (`A.B.C`).** `A` = roadmap version (v0→0 … v2→2), `B` = phase within it (`v1.3` → `1.3.0`), `C` = a post-release fix on that phase. Roadmap phase `vA.B` → semver `A.B.0`; a fix after it bumps `C`. Releases are cut per phase. Never bump the version without explicit confirmation.

---

## v0 — Groundwork: text from the receiver's audio, the piece model proven

Remove the two unknowns everything else rests on — **whether CW decoded on the Mac from a public receiver's audio gives usable text**, and **whether the piece model explains it well enough** — before any product code is written. The text comes from **sruti's own decoder**: the receiver's `CW_decoder` extension is missing or disabled on many receivers, and where it exists it did not run for sruti's connections (v0.1 findings, ARCHITECTURE §The receiver). Both phases are spikes and measurements, not product code: v0.1 gets the receiver's audio onto the Mac, decodes it with a prototype and records the sessions every later test replays; v0.2 turns the model comparison in [poc/RESULTS.md](../poc/RESULTS.md) into a measured baseline on golden examples. Depends on: nothing — this is the foundation.

### v0.1 — Text from the receiver, decoded on the Mac

**Goal:** CW from a public KiwiSDR's audio is decoded into text on the Mac by a prototype decoder.

A spike that connects to a public KiwiSDR the way its browser page does — the connection timestamp from `/VER`, the `/ws/` socket path — opens one CW audio channel tuned to the signal's own frequency, and records the 12 kHz audio as WAV beside a raw capture of the text messages (ARCHITECTURE §The receiver). A **prototype decoder** turns the audio into text: it finds the CW tone in the passband, follows its envelope with an adaptive threshold, adapts to the sending speed and maps Morse to characters (ARCHITECTURE §The decoder). `kiwiclient` has no license, so it serves only this spike. The recordings become the fixtures for the fake receiver and the material for golden examples; the messages observed become the capture inspector's vocabulary (v1.5).

**Tasks:**
- **The spike:** one CW audio channel, connected like the browser page, tuned to the signal frequency; the audio recorded as WAV and the text messages as a raw capture.
- **The prototype decoder:** audio → text, with a self-test on synthetic CW (known text, several speeds and noise levels, and an empty passband that must decode to nothing).
- **Receiver:** the owner's receiver (Trémolat, `sdr.autreradioautreculture.com:8073`); any other must be reachable from the Mac — the corporate web filter blocks dynamic-DNS hosts — with good HF reception and a free slot.
- **License:** check `kiwiclient`'s license before depending on it (the checkout has no license file).
- **Recordings:** record sessions as WAV + capture — a CQ run and a conversation — and decode each on the Mac. (The 14.100 MHz beacon recording moved to v1.2 on 2026-10-04: 20 m had not opened during v0.1's recording window.)
- **Message inventory:** note every message type the audio channel carries and how it parses — the raw material for the config panel's capture inspector (v1.5).

**DoD:** a live conversation in 7.000–7.040 or 14.000–14.070 MHz decodes to readable text on the Mac; the recordings are saved.

**Tests:** the prototype decoder's synthetic self-test; the recordings become fixtures.

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

## v1 — The listening agent: receiver link, CW decoder, pieces and sessions, piece explainer, the desktop app, session explainer

The product, built from the core outward. v1.1 stands up the project and the **receiver link**, which streams the channel's audio. v1.2 turns the audio into characters with **sruti's own CW decoder**, and a headless CLI prints them. v1.3 cuts the stream into **pieces** and saves everything as **sessions** that can be named, switched and reopened. v1.4 adds the **piece explainer** (sections 2–3, Gemini 3.8 Flash). v1.5 puts it all in the **desktop window** — the four sections, the config panel with the capture inspector, the session switcher. v1.6 fills section 4 with the **session explainer** (Claude Opus 5.5, only on the Explain press). The core never imports the app: the window is a shell over the core's events and commands, talking through the pywebview bridge with no port (ARCHITECTURE §Core and the desktop app). Depends on: v0 (the recordings that become fixtures, the prototype decoder, the prompt and glossary form).

### v1.1 — Project skeleton and the receiver link

**Goal:** `sruti listen --receiver <host:port> --freq <kHz>` connects to a receiver and streams the channel's audio, with link states and the raw messages, as events (headless; characters arrive in v1.2).

The Python project, its configuration and the **receiver link** — sruti's own WebSocket client for the audio channel, written from the protocol the v0.1 captures show (`kiwiclient` has no license and stays out of the product). It connects like the receiver's browser page, tunes the channel to the signal frequency, takes uncompressed 12 kHz audio, and emits audio blocks with timestamps, the signal level, link states and the **raw messages** on the core event stream. It reconnects with backoff; "receiver busy", "all free channels taken" and "time limit reached" are states, not crashes. Listen only, and a polite guest: one connection per run, identified as `sruti`, nothing sent beyond the documented tuning messages. Depends on: v0.1.

**Tasks:**
- **The project:** Python with `uv`, ruff, pytest and CI.
- **Configuration:** the config file (`sruti.toml`) and `.env`.
- **The receiver link:** the `receiver` module — sruti's own client for the audio channel — emitting audio blocks, the signal level and the raw messages as events.
- **Robustness:** reconnect with backoff; busy, no-free-channel and time-limit states.

**DoD:** an hour of listening survives a dropped connection; a recorded session replays to the same audio and messages.

**Tests:** unit — message parsing, audio frame unpacking, link states; integration — the fake receiver replays a recorded session.

### v1.2 — The CW decoder

**Goal:** the channel's audio becomes a character stream with timestamps, live, at the quality the v0.1 prototype reached or better.

The product version of the v0.1 prototype, in the `decoder` component: it follows the CW tone in the passband, keys on an adaptive threshold with hysteresis, rejects an empty passband, adapts to the sending speed as it changes, and maps Morse to characters — prosigns as strings, unknown codes as `[err]`, never a guess. It runs on the live audio in small blocks and emits characters with timestamps plus its status (tone, speed, signal-over-noise) for the inspector (ARCHITECTURE §The decoder). `sruti listen` prints the characters. Depends on: v1.1 (audio), v0.1 (the prototype and the recordings to tune on).

**Tasks:**
- **The decoder:** tone detection, envelope, adaptive threshold, speed tracking, Morse table — streaming, on blocks of live audio.
- **Status:** tone, speed and signal-over-noise as events, for the capture inspector.
- **The beacon recording** (carried over from v0.1): 14.100 MHz on Trémolat while 20 m is open, at least one full 3-minute NCDXF cycle, saved as a fixture beside the v0.1 recordings.
- **Tuning:** the parameters in configuration, tuned on the v0.1 recordings.
- **The CLI:** `sruti listen` prints the decoded characters as they arrive.

**DoD:** on the beacon recording the beacon call signs (e.g. `OH2B`) decode; on the recorded conversation the text reads at least as well as the prototype's; an empty passband decodes to nothing.

**Tests:** unit — each stage on synthetic CW (speeds, noise, fading, an empty passband) and streaming in blocks equals decoding the whole recording; regression — the v0.1 recordings against their expected text.

### v1.3 — Pieces and the session store

**Goal:** the character stream is cut into pieces, and everything is saved as sessions that can be reopened.

The pure **segmenter** closes a piece on an end-of-turn prosign standing alone, on 3 s of silence or at 200 characters; the piece is the piece tier's buffer. **Sessions are manual**: on launch sruti connects with the `sruti.toml` defaults and that opens the first one; retuning closes it and opens the next; `SK` and silence close pieces, never sessions. The **store** writes one append-only JSONL file per session in the record shapes of ARCHITECTURE §Pieces and sessions, and replays a saved session into the same event stream, read-only. Depends on: v1.2.

**Tasks:**
- **The segmenter:** pure characters → pieces; thresholds in configuration, tuned on the v0.1 recordings.
- **The store:** one append-only JSONL file per session under `var/sessions/` with the records from ARCHITECTURE.md, starting with the `session` header (auto name from date · receiver · frequency; rename appends a new header, latest wins).
- **Manual session boundaries:** a retune closes the session and opens a new one.
- **Replay:** a saved session replays into the event stream.

**DoD:** on the recorded conversation, pieces end where the operators hand over; a saved session replays identically; retuning starts a new session file; a rename survives reopening and never touches the file name.

**Tests:** unit — every piece rule, timing edge cases, store round-trip and replay, naming and rename.

### v1.4 — Piece explainer

**Goal:** within 5 s of a piece closing, its word-by-word gloss and its English message translation (sections 2 and 3) exist.

One call per **closed piece**: instructions and glossary (the stable prefix) + the last raw pieces + the recent section-3 entries + the new piece → Gemini 3.8 Flash with a response schema → `{gloss, action, message/rebuilt}`. The gloss is the literal layer, every token covered; the message is the communicative layer — what was said, CW repeats collapsed, nothing invented; the action is `none` (a repeat, shown as a ×n counter), `append` (one new entry) or `rebuild` (a marked replacement of the recent entries the model was shown). Both sections are append-only on screen and the store stays append-only (ARCHITECTURE §The four sections). Depends on: v0.2 (the prompt and glossary form), v1.3 (pieces).

**Tasks:**
- **The glossary:** the `glossary/` data file in the form settled in v0.2.
- **Prompt assembly**, with the stable prefix first.
- **The Gemini API client:** structured output against the `{gloss, action, message/rebuilt}` schema, thinking level low, the key in the request header.
- **Buffering is the piece** — never word-by-word calls.
- **Cost:** the running cost summed per session.
- **Degrade:** on failure or without a Gemini key, raw text only.

**DoD:** on example 001 the model reaches the bar set in v0.2, inside the budget.

**Tests:** unit — prompt assembly, schema validation, error paths (mocked Gemini client); eval — golden examples, opt-in.

### v1.5 — The desktop app

**Goal:** `uv run sruti app` opens the four-section window — original text, word by word, message, what is going on — with the config panel and the session switcher.

A native macOS window from **pywebview** on the system WebKit. The page — one HTML file with inline CSS and JavaScript — is the **Claude Design deliverable** made against [design/BRIEF.md](design/BRIEF.md), handed to the window as a string, so no HTTP server starts. The **bridge** object exposes the core commands to the page, and Python pushes core events in with `evaluate_js` — no socket, no port, not even on loopback (ARCHITECTURE §Core and the desktop app). `poc/desktop/` is the working prototype for the Python side. Depends on: v1.3 (sessions to switch and replay), v1.4 (sections 2–3).

**Tasks:**
- **The window:** pywebview on the core event stream; the page as one inline HTML file handed to the window as a string.
- **The bridge:** the bridge object exposing the core commands to the page; core events pushed in with `evaluate_js`.
- **The four sections:** section 1 streams live, sections 2–3 fill as each piece closes, section 4 is the Explain pane (wired in v1.6, showing "Explain off" until then).
- **The header:** the session name (click to rename), receiver, frequency, link status and running costs.
- **The config panel:** receiver, frequency, decoder parameters, languages — with the **capture inspector** showing the raw messages and the decoder status next to how each parsed, applied on reconnect.
- **The session switcher:** list saved sessions by name, open one as a read-only replay, start a new session by retuning, and **rename** the current or a past session in place.
- **The page:** the Claude Design deliverable made against `specification/design/BRIEF.md`; `poc/desktop/` is the working prototype for the Python side.

**DoD:** a recorded session replayed through the fake receiver fills sections 1–3 live in the window; the connection settings can be changed from the panel and the raw traffic is visible; a past session can be opened, a new one started by retuning, and a session renamed from the app; no listening socket exists while the app runs.

**Tests:** unit — the bridge object driven over the fake receiver with a fake window recording every `evaluate_js` call (commands in, events out, in order); a test that the window is created from a string with no HTTP server; the page rendered from a recorded snapshot in a headless browser, opt-in.

### v1.6 — Session explainer

**Goal:** pressing **Explain** fills section 4 with a whole-session explanation in Ukrainian at the quality of the reference answer.

The **Explain** press sends the whole session — glossary and every piece so far — to Claude Opus 5.5 (Fable 5.1 by configuration) and renders the Ukrainian explanation in section 4, rebuilt wholesale on every press. Only on the press: never on a timer, at session end or on reconnect. While a call runs the button is disabled; a failed call keeps the previous explanation with an error note; without a Claude key section 4 reads "Explain off" and everything else works (ARCHITECTURE §The four sections). Depends on: v1.5 (the button), v1.3 (the session), v0.2 (the golden examples).

**Tasks:**
- **The Claude API client:** Opus 5.5 by default, Fable 5.1 by configuration.
- **The `explain` command**, wired from the app's Explain button to the call.
- **Prompt caching** on the stable prefix.
- **Cost:** per-call cost shown and summed per session.
- **Off without a key:** without a Claude key the button reports Explain is off.

**DoD:** on example 001 the output matches the reference answer in substance; without a Claude key everything except section 4 works, without errors; no call ever happens without a press.

**Tests:** unit — trigger handling, cost accounting, mocked client; eval — golden examples, opt-in.

---

## v2 — Finding traffic (open)

The agent chooses where to listen. To be decided once v1 is in use: choose receivers from the public directory by band, load and reception; scan CW band segments on the receiver's waterfall for active signals; follow DX-cluster or Reverse Beacon Network spots; stay with a conversation while it lasts. Depends on: v1.

---

## Contract mapping

- **Receiver messages** (ARCHITECTURE §The receiver) — observed in **v0.1**, implemented by the receiver link in **v1.1**, shown raw in the capture inspector in **v1.5**.
- **The decoder** (ARCHITECTURE §The decoder) — prototype in **v0.1**, product in **v1.2**; its status in the capture inspector in **v1.5**.
- **CLI** — `sruti listen --receiver <host:port> --freq <kHz>` in **v1.1** (audio; `--record`, `--raw`) and **v1.2** (characters); `sruti app` in **v1.5**.
- **Segmenter rules and thresholds** (end-of-turn prosigns, pause, length cap; in configuration) — **v1.3**.
- **Record shapes and the session store layout** — `session`, `char`, `piece` and `var/sessions/<started>-<receiver>-<freq>.jsonl` in **v1.3**; `explanation` with `tier: "piece"` in **v1.4**; with `tier: "session"` in **v1.6**.
- **Core commands** (`tune`, `start`/`stop`, `open-session`, `rename-session`, `set-config`) — in the core from **v1.3**, exposed to the page through the bridge in **v1.5**; `explain` wired in **v1.6**.
- **Piece explainer schema** `{gloss, action, message/rebuilt}` and its three actions — the prompt settled in **v0.2**, the client in **v1.4**.
- **Four-section display contract** and the page's event and command names ([design/BRIEF.md](design/BRIEF.md) §8) — **v1.5**.
- **Two-tier table** — the piece tier in **v1.4**, the session tier in **v1.6**.

## Deferred

A call-sign prefix → country lookup from a maintained table (e.g. the CTY files), not from model memory; the receiver's own `CW_decoder` extension as an optional second text source where it is enabled and runs; own SDR hardware on `ich-picobox`, behind the same receiver interface — beyond v0–v2.
