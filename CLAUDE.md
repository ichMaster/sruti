# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification

Read these before planning work; they are the project's contract with itself.

- **[specification/MISSION.md](specification/MISSION.md)** — what sruti is, for whom, the principles
  (incl. "listen only" and "never invent"), the non-goals, and the glossary. A request that violates a
  non-goal is a conversation, not a task.
- **[specification/ARCHITECTURE.md](specification/ARCHITECTURE.md)** — the core/interface split, the
  KiwiSDR protocol, the four-section display contract, pieces and sessions, the two model tiers, the
  config panel, the hosts, and testing. Both interface architectures (TUI v1, web v2) live here.
- **[specification/ROADMAP.md](specification/ROADMAP.md)** — versions v0 (groundwork) through v4, each
  phase `vA.B` with Goal, Tasks, DoD and Tests. Build phases strictly in order and check each against its
  DoD before moving on. v3 and v4 are not broken into phases yet.
- **[specification/examples/](specification/examples/)** — golden examples; example 001 is the quality bar
  for the explainers.

## Project status

A private listening agent for one user: it tunes into a public KiwiSDR, reads the decoded Morse (CW) text,
and shows four sections — the original text (live), a word-by-word gloss and an English message
translation (local model via Ollama, per buffered piece), and a Ukrainian explanation of what is going on
(Claude Opus 5.5, **only when the user presses Explain**). Sessions are switched manually (switching =
retuning), always saved, and replayable. v1 is a TUI; v2 is the same thing in the browser on localhost.
So far the repo holds only the specification.

Latest release: none yet.

| Version | Phases | What it delivers |
|---|---|---|
| `v0` Groundwork | v0.1 text from the receiver · v0.2 choose the local model | spikes, recordings, golden examples, a model decision |
| `v1` The listening agent (TUI) | v1.1 skeleton + receiver link · v1.2 pieces + session store · v1.3 local explainer · v1.4 the TUI · v1.5 cloud explainer | first real code in v1.1 |
| `v2` The web interface | v2.1 local web server · v2.2 browser UI | the same four sections on `127.0.0.1` only |
| `v3` Decoding on the Mac | (not yet phased) | a local CW decoder as a second text source |
| `v4` Finding traffic | (open) | the agent chooses where to listen |

## Layout and commands

The components (ARCHITECTURE.md §Components): `receiver` (the KiwiSDR link on `kiwiclient`, also emitting
the raw extension messages), `segmenter` (pure characters → pieces), `store` (append-only JSONL sessions
under `var/sessions/`, listing and replay), `glossary/` (versioned data), `explain/local` (Ollama, gloss +
message), `explain/cloud` (Claude API, on the Explain action), `ui/tui` (Textual, v1), `ui/web` (FastAPI
on localhost, v2). The core never imports interface code.

- Headless (from v1.1): `uv run sruti listen --receiver <host:port> --freq <kHz>`
- The TUI (from v1.4): `uv run sruti tui` — four sections, the config panel with the capture inspector,
  the session switcher.
- The web interface (from v2.1): `uv run sruti web` — bound to `127.0.0.1` only.
- Configuration lives in `sruti.toml`; recordings and session files are local data (`var/`, gitignored);
  curated recordings become fixtures and golden examples under `specification/examples/`.
- `.env` (gitignored) holds only the Claude API key. Never print it or commit it; the agent must run fully
  without it (local-only).

## Acceptance gates

Automated gates need no network: tests mock Ollama and the Claude API, drive the receiver link with the
fake receiver (replayed recordings), drive the TUI headless (Textual pilot), and inject the clock. Nothing
reaches a receiver or a paid API.

| Gate | Command | When |
|---|---|---|
| Lint | `uv run ruff check .` | any Python change |
| Tests | `uv run pytest` (one test: `uv run pytest tests/test_x.py::test_name`) | any Python change |

- **Before v1.1:** there is no `pyproject.toml`, so the Python gates are `n/a`, not passed. ruff and pytest
  are dev dependencies, added by the issue that creates `pyproject.toml`.
- **Opt-in, never automatic:** the golden-example eval (real models over `specification/examples/`) and the
  live check (the 14.100 MHz beacons on a real receiver). Run them only when the owner asks.
- **Manual gates:** the ROADMAP DoD items marked **Manual (owner)** need a live receiver, a real model run
  or a quality judgment against the reference answer.
  - Claude may run the offline checks (replays, fixtures) itself.
  - Anything that connects to a public receiver, calls Ollama or the Claude API for real, or judges
    explanation quality is done or confirmed by the owner.
  - A manual check counts as passed only once the owner confirms it.

## Rules that are easy to break

The full mechanisms live in ARCHITECTURE.md; these are the invariants most often broken by accident:

- **Listen only.** No code path transmits, keys or talks back on the air; nothing is sent to the receiver
  beyond the documented tuning and decoder `SET` messages.
- **A polite guest.** One connection per run, identified as `sruti`; back off from a busy receiver,
  respect its time limits, disconnect when idle.
- **Never invent.** Unreadable text is `[...]`, not guessed; a call sign is never "corrected" into a
  different call sign; the decoder's `[err]` is handled; uncertainty is said out loud.
- **The cloud tier runs only on the user's Explain action.** Never on a timer, never automatically — not
  at session end, not on reconnect. Every call's cost is shown and summed per session.
- **The local tier is buffered by piece**, never called word by word as characters arrive.
- **Sessions are manual and always saved.** A session ends only on retune or quit; switching the session
  *is* retuning; `SK` and silence close pieces, never sessions; a past session is replayed read-only and
  never rewritten.
- **Languages:** sections 2–3 (gloss, message) in English; section 4 (the explanation) in Ukrainian; both
  from configuration. Call signs, Q-codes and quoted original text stay as sent.
- **Degrade, don't crash.** Ollama down → the piece shows raw text only; no API key → Explain reports the
  cloud tier is off; a dropped link reconnects with backoff; a failed model call never kills the listening
  loop.
- **The core never imports interface code.** The TUI and the web page consume the same events and send the
  same commands; new behavior goes into the core, not into an interface.
- **The web interface binds to `127.0.0.1` only** — never to a LAN interface. A test pins the binding.
- **The glossary is data.** Q-codes, prosigns and abbreviations live in `glossary/` and are rendered into
  the prompts — never hardcoded, never left to model memory.
- **Keep decisions pure**: the piece cut rules, `cw_chars` decoding, prompt assembly, schema validation,
  the Explain trigger handling and the cost accounting are functions over plain data with an injected
  clock.
- **Everything is logged to the session store** — every character, piece and explanation with timestamps —
  and a session replays to the same text.
- **Secrets stay out**: never print `.env`; the API key never goes into argv, logs, commits or issue
  comments. To check a value is set, test it without echoing it (`grep -q '^ANTHROPIC_API_KEY=.' .env`).

## Contracts

Changing any of these updates ARCHITECTURE.md and the test that pins it, in the same commit:

- the **four-section display contract**: what each section shows, which tier feeds it, and when it updates
  (ARCHITECTURE.md §The four sections);
- the **record shapes** (`char`, `piece`, the two `explanation` forms) — also the session-store lines
  (§Pieces and sessions);
- the **segmenter rules and thresholds** (end-of-turn prosigns, pause, length cap), with the thresholds
  living in configuration;
- the **local explainer's JSON schema** `{gloss, message}`;
- the **core commands** an interface may send (`tune`, `start`/`stop`, `explain`, `open-session`,
  `set-config`);
- the **CLI**: `sruti listen --receiver <host:port> --freq <kHz>`, `sruti tui`, `sruti web`;
- the **session store layout** (`var/sessions/<started>-<receiver>-<freq>.jsonl`, append-only);
- the **KiwiSDR extension messages** sruti sends and reads (the table in ARCHITECTURE.md §The receiver);
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
  connection is opened outward (receiver WebSocket, Ollama on `localhost:11434`, the Claude API), and the
  v2 web server is localhost-only.
- Public receivers have few slots; recordings exist so that development and tests don't occupy one.
- The cloud tier costs money (Opus ≈ $0.03 per press). It runs only on the user's action, the cost is
  always visible, and no test or gate ever calls a paid API.
- `kiwiclient`'s license must be checked (v0.1) before the project depends on it.
