# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification

Read these before planning work; they are the project's contract with itself.

- **[specification/MISSION.md](specification/MISSION.md)** — what sruti is, for whom, the principles
  (incl. "listen only" and "never invent"), the non-goals, and the glossary. A request that violates a
  non-goal is a conversation, not a task.
- **[specification/ARCHITECTURE.md](specification/ARCHITECTURE.md)** — the core and the desktop app
  (pywebview window, JS bridge, no port), the KiwiSDR protocol, the four-section display contract, pieces
  and sessions, the two model tiers, the config panel, the hosts, and testing.
- **[specification/ROADMAP.md](specification/ROADMAP.md)** — versions v0 (groundwork) through v2, each
  phase `vA.B` with Goal, Tasks, DoD and Tests. Build phases strictly in order and check each against its
  DoD before moving on. v2 is not broken into phases yet.
- **[specification/examples/](specification/examples/)** — golden examples; example 001 is the quality bar
  for the explainers.

## Project status

A private listening agent for one user: it tunes into a public KiwiSDR, decodes the Morse (CW) in its
audio on the Mac with its own decoder, and shows four sections — the original text (live), a word-by-word gloss and an English message
translation (Gemini 3.8 Flash, per buffered piece), and a Ukrainian explanation of what is going on
(Claude Opus 5.5, **only when the user presses Explain**). Sessions are switched manually (switching =
retuning), always saved, and replayable. The interface is a desktop window (pywebview); nothing listens.
So far the repo holds the specification and the PoCs (`poc/`): the v0.1 receiver spike and prototype
decoder, the model comparison, and the desktop-window prototype.

Latest release: v0.2.0 (phase v0.2 — prove the piece model).

| Version | Phases | What it delivers |
|---|---|---|
| `v0` Groundwork | v0.1 text from the receiver, decoded on the Mac · v0.2 prove the piece model | the receiver spike, a prototype decoder, recordings, golden examples, the prompt and glossary form |
| `v1` The listening agent (desktop app) | v1.1 skeleton + receiver link · v1.2 the CW decoder · v1.3 pieces + session store · v1.4 piece explainer · v1.5 the desktop app · v1.6 session explainer | first real code in v1.1 |
| `v2` Finding traffic | (open) | the agent chooses where to listen |

## Layout and commands

The components (ARCHITECTURE.md §Components): `receiver` (the KiwiSDR link — sruti's own WebSocket client for one audio
channel — also emitting the raw messages), `decoder` (sruti's own CW decoder: audio → characters),
`segmenter` (pure characters → pieces), `store` (append-only JSONL sessions
under `var/sessions/`, listing and replay), `glossary/` (versioned data), `explain/piece` (Gemini 3.8
Flash, gloss + message per piece), `explain/session` (Claude Opus 5.5, on the Explain action), `ui/app`
(the pywebview window, its page and the bridge). The core never imports the app's code.

The package lives in `src/sruti/` (from v1.1: `config.py`, `events.py` — the event stream, `cli.py`, and
`receiver/`), the tests in `tests/`, the PoCs in `poc/`. Set up once with `uv sync`.

- Headless (from v1.1, characters from v1.2): `uv run sruti listen --receiver <host:port> --freq <kHz>`
  — link states and the level every 10 s; `--raw` prints the raw messages, `--record <dir>` writes WAV +
  capture.
- The app (from v1.5): `uv run sruti app` — the window with the four sections, the config panel with the
  capture inspector, the session switcher. The working prototype is `poc/desktop/`.
- Configuration: defaults in `src/sruti/config.py`, overridden by an optional `sruti.toml` (gitignored; see
  `sruti.example.toml`); recordings and session files are local data (`var/`, gitignored);
  curated recordings become fixtures and golden examples under `specification/examples/`.
- `.env` (gitignored) holds the two API keys: `GEMINI_API_KEY` (piece tier) and `ANTHROPIC_API_KEY`
  (session tier). Never print it or commit it. Without a key its tier is off and everything else keeps
  working.

## Acceptance gates

Automated gates need no network: tests mock the Gemini and Claude APIs, drive the receiver link with the
fake receiver (replayed recordings), drive the app's bridge with a fake window, and inject the clock. Nothing
reaches a receiver or a paid API.

| Gate | Command | When |
|---|---|---|
| Lint | `uv run ruff check .` | any Python change |
| Tests | `uv run pytest` (one test: `uv run pytest tests/test_x.py::test_name`) | any Python change |

- **From v1.1** the gates apply to every change: ruff and pytest are dev dependencies pinned in `uv.lock`,
  ruff's rule set is explicit in `pyproject.toml`, and GitHub Actions (`.github/workflows/ci.yml`) runs
  both on every push. Releases before v1.1 recorded the Python gates as `n/a`.
- **Opt-in, never automatic:** the golden-example eval (real models over `specification/examples/`) and the
  live check (the 14.100 MHz beacons on a real receiver). Run them only when the owner asks.
- **Manual gates:** the ROADMAP DoD items marked **Manual (owner)** need a live receiver, a real model run
  or a quality judgment against the reference answer.
  - Claude may run the offline checks (replays, fixtures) itself.
  - Anything that connects to a public receiver, calls the Gemini or Claude API for real, or judges
    explanation quality is done or confirmed by the owner.
  - A manual check counts as passed only once the owner confirms it.

## Rules that are easy to break

The full mechanisms live in ARCHITECTURE.md; these are the invariants most often broken by accident:

- **Listen only.** No code path transmits, keys or talks back on the air; nothing is sent to the receiver
  beyond the documented tuning messages.
- **A polite guest.** One connection per run, identified as `sruti`; back off from a busy receiver,
  respect its time limits, disconnect when idle.
- **Never invent.** Unreadable text is `[...]`, not guessed; a call sign is never "corrected" into a
  different call sign; the decoder's `[err]` is handled; uncertainty is said out loud.
- **The session tier runs only on the user's Explain action.** Never on a timer, never automatically —
  not at session end, not on reconnect. Every call's cost is shown and summed per session.
- **The piece tier is buffered by piece**, never called word by word as characters arrive. It spends
  automatically, so its running cost is summed per session and shown.
- **Sessions are manual, named, and always saved.** A session ends only on retune or quit; switching the
  session *is* retuning; `SK` and silence close pieces, never sessions; a past session is replayed
  read-only and never rewritten. Every session is auto-named on open and renameable from the app at any
  time — a rename appends a `session` record and never renames the file.
- **Languages:** sections 2–3 (gloss, message) in English; section 4 (the explanation) in Ukrainian; both
  from configuration. Call signs, Q-codes and quoted original text stay as sent.
- **Degrade, don't crash.** No Gemini key, no network or a failed call → the piece shows raw text only; no
  Claude key → Explain reports it is off; a dropped link reconnects with backoff; a failed model call never
  kills the listening loop.
- **The core never imports the app's code.** The window consumes the core's events and sends its commands;
  new behavior goes into the core, not into the page.
- **Nothing listens.** The page is handed to the pywebview window as a string and talks to Python only
  through the JS bridge — no HTTP server, no port, not even on loopback. A test pins it.
- **The glossary is data.** Q-codes, prosigns and abbreviations live in `glossary/` and are rendered into
  the prompts — never hardcoded, never left to model memory.
- **Keep decisions pure**: the decoder's stages, the piece cut rules, prompt assembly, schema validation,
  the Explain trigger handling and the cost accounting are functions over plain data with an injected
  clock.
- **Everything is logged to the session store** — every character, piece and explanation with timestamps —
  and a session replays to the same text.
- **Secrets stay out**: never print `.env`; an API key never goes into argv, logs, commits, issue comments
  or a URL (the Gemini key travels in the `x-goog-api-key` header). To check a value is set, test it without
  echoing it (`grep -q '^GEMINI_API_KEY=.' .env`).

## Contracts

Changing any of these updates ARCHITECTURE.md and the test that pins it, in the same commit:

- the **four-section display contract**: what each section shows, which tier feeds it, and when it updates
  (ARCHITECTURE.md §The four sections);
- the **record shapes** (the `session` header, `char`, `piece`, the two `explanation` forms) — also the
  session-store lines (§Pieces and sessions);
- the **segmenter rules and thresholds** (end-of-turn prosigns, pause, length cap), with the thresholds
  living in configuration;
- the **piece explainer's JSON schema** `{gloss, action, message/rebuilt}` and its three actions (none ·
  append · rebuild-of-window);
- the **core commands** the page may send through the bridge (`tune`, `start`/`stop`, `explain`, `open-session`,
  `rename-session`, `set-config`);
- the **CLI**: `sruti listen --receiver <host:port> --freq <kHz> [--record <dir>] [--raw]`, `sruti app`;
- the **session store layout** (`var/sessions/<started>-<receiver>-<freq>.jsonl`, append-only);
- the **receiver messages** sruti sends and reads, and how it connects (ARCHITECTURE.md §The receiver);
- the **decoder's output**: characters with timestamps, prosigns as strings, unknown codes as `[err]`
  (§The decoder);
- the **two-tier table** (when each tier runs, its inputs, languages, budgets and fallbacks).

## Delivery workflow (skills)

`.claude/skills/` holds a spec-driven pipeline adapted from the matrix-agora project.

- **Issues:** each ROADMAP phase `vA.B` becomes `specification/implementation/vA.B-issues.md`. Issue ids
  are `SRUTI-###`, numbered globally and never reset.
- **Implementation:** each issue is one commit. Each phase is then reviewed, and the fix-now findings are
  fixed.
- **Releases:** phase `vA.B` ships as `A.B.0` (tag `vA.B.0`); post-release fixes bump the last digit
  (`A.B.1`, …).
- **GitHub flow:** `/ship-phase <selector>` (a phase `vA.B`, a version `vA`, or a range) runs
  `/generate-issues` → `/upload-issues` → `/execute-issues` → `/review-and-fix-issues` →
  `/release-version` for each phase, then `/harden-findings` at the end of the run.
- **Offline flow:** `/ship-solution` runs `/reconcile-issues` → `/execute-issues-file` →
  `/review-and-fix-issues` → `/release-version` over issues files that already exist.
- **Who releases:** versions are bumped and tagged only by `/release-version`, `/ship-phase`,
  `/ship-solution` or `/harden-findings --release`.

## Constraints

- The Mac is managed: no SDR software, no inbound connections (endpoint filtering destroys them); every
  connection is opened outward (receiver WebSocket, the Gemini API, the Claude API), and nothing in sruti
  listens on any port. sruti runs from the repo with `uv`; a packaged `.app` is not planned.
- Public receivers have few slots; recordings exist so that development and tests don't occupy one.
- Both tiers cost money: the piece tier ≈ $0.0026 per piece (≈ $0.26 per hour of lively traffic,
  doubling in 2027; measured in v0.2), the session tier ≈ $0.03 per Explain press. The costs are always visible, and no test or gate
  ever calls a paid API.
- `kiwiclient` has no license: only the v0.1 spike uses it, from an uncommitted checkout in `var/kiwiclient/`.
  The `receiver` module is sruti's own client; never vendor, copy or depend on `kiwiclient` in the product.
