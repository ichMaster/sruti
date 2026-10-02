# Roadmap — sruti

Versions are built in order; phases inside a version are numbered `vA.B`. Each phase has a **Goal**, **Tasks**, a **Definition of Done (DoD)** and **Tests**.

v0 removes the two unknowns everything else rests on — whether the receiver's decoder delivers usable text, and whether a local model is good enough — before any product code is written.

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

**DoD:** on 14.100 MHz the beacon call signs (e.g. `OH2B`) appear as text; a live conversation in 7.000–7.040 or 14.000–14.070 MHz produces readable text; the recordings are saved.

**Tests:** none automated — a spike. Its recordings become fixtures.

### v0.2 — Choose the local model

**Goal:** a local model that is good and fast enough — or a recorded decision that none is.

**Tasks:**
- Turn example 001 and the v0.1 recordings into golden examples: raw text plus a reference explanation from the cloud tier.
- Run `gemma4:12b`, `qwen3.5:9b` and any newer candidate with the same prompt and schema; record quality notes and latency.
- For models that fail in one step, try two: restore the text in its own language, then translate.

**DoD:** a model is chosen with its measured latency per piece; or the local tier is cut down to what a small model does well (e.g. glossary expansion only), and the decision is written into ARCHITECTURE.

**Tests:** the golden-example eval script, opt-in.

---

## v1 — The listening agent

### v1.1 — Project skeleton and the receiver link

**Goal:** `sruti listen --receiver <host:port> --freq <kHz>` streams decoded text to the terminal.

**Tasks:** Python project (`uv`, ruff, pytest, CI); the `receiver` module on `kiwiclient`; reconnect with backoff; busy and time-limit states; the session log.

**DoD:** an hour of listening survives a dropped connection; a session log replays to the same text.

**Tests:** unit — `cw_chars` decoding, link states; integration — the fake receiver replays a recorded session.

### v1.2 — Pieces and sessions

**Goal:** the character stream is cut into pieces and sessions by the rules in ARCHITECTURE.

**Tasks:** the pure `segmenter`; thresholds in configuration; tuning on the v0.1 recordings.

**DoD:** on the recorded conversation, pieces end where the operators hand over.

**Tests:** unit — every piece and session rule, timing edge cases.

### v1.3 — Local explainer

**Goal:** every piece gets L1 and L2 in Ukrainian within 5 s.

**Tasks:** the `glossary/` data file; prompt assembly; Ollama client with a JSON schema; L1/L2 under each piece; on failure, raw text only.

**DoD:** on example 001 the chosen model reaches the bar set in v0.2, inside the budget, on the Mac.

**Tests:** unit — prompt assembly, schema validation, error paths (mocked model); eval — golden examples, opt-in.

### v1.4 — Cloud explainer

**Goal:** every few minutes, a full explanation of the session at the quality of the reference answer.

**Tasks:** Claude API client (Opus 5.5 by default, Fable 5.1 by configuration); the timer, the "new text only" rule and the session-end call; prompt caching on the stable prefix; an hourly cost cap; a display block that supersedes local output.

**DoD:** on example 001 the output matches the reference answer in substance; without an API key the agent runs local-only, without errors.

**Tests:** unit — scheduling rules, cost cap, mocked client; eval — golden examples, opt-in.

---

## v2 — Decoding on the Mac

**Goal:** a second text source, for receivers without the decoder extension or when its decoding is poor.

Audio from the same receiver channel → a local CW decoder (tone detection, adaptive timing) → the same character stream. Compared with the receiver's decoder on recorded audio; the source is selectable per run.

## v3 — Finding traffic (open)

**Goal:** the agent chooses where to listen.

To be decided once v1 is in use: choose receivers from the public directory by band, load and reception; scan CW band segments on the receiver's waterfall for active signals; follow DX-cluster or Reverse Beacon Network spots; stay with a conversation while it lasts.

## Later

- Call-sign prefix → country from a maintained table (e.g. the CTY files), not from model memory.
- Own SDR hardware on `ich-picobox`, behind the same receiver interface.
