# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification

Read these before planning work; they are the project's contract with itself.

- **[specification/MISSION.md](specification/MISSION.md)** — what sruti is, for whom, the principles
  (incl. "listen only" and "never invent"), the non-goals, and the glossary. A request that violates a
  non-goal is a conversation, not a task.
- **[specification/ARCHITECTURE.md](specification/ARCHITECTURE.md)** — components, the KiwiSDR protocol,
  pieces and sessions, the two model tiers, the hosts, and testing.
- **[specification/ROADMAP.md](specification/ROADMAP.md)** — versions v0 (groundwork) through v3, each
  phase `vA.B` with Goal, Tasks, DoD and Tests. Build phases strictly in order and check each against its
  DoD before moving on. v2 and v3 are not broken into phases yet.
- **[specification/examples/](specification/examples/)** — golden examples; example 001 is the quality bar
  for the explainers.

## Project status

A private listening agent for one user: it tunes into a public KiwiSDR, reads the decoded Morse (CW) text,
and explains it in Ukrainian at two levels — each piece instantly via a local model (Ollama), the whole
conversation periodically via the Claude API. So far the repo holds only the specification.

Latest release: none yet.

| Version | Phases | What it delivers |
|---|---|---|
| `v0` Groundwork | v0.1 text from the receiver · v0.2 choose the local model | spikes, recordings, golden examples, a model decision |
| `v1` The listening agent | v1.1 skeleton + receiver link · v1.2 pieces and sessions · v1.3 local explainer · v1.4 cloud explainer | first real code in v1.1 |
| `v2` Decoding on the Mac | (not yet phased) | a local CW decoder as a second text source |
| `v3` Finding traffic | (open) | the agent chooses where to listen |

## Layout and commands

The components (ARCHITECTURE.md §Components): `receiver` (the KiwiSDR link on `kiwiclient`), `segmenter`
(pure characters → pieces → sessions), `glossary/` (versioned data), `explain/local` (Ollama),
`explain/cloud` (Claude API), `ui` (terminal), `log` (JSONL session log).

- Run (from v1.1): `uv run sruti listen --receiver <host:port> --freq <kHz>`
- Recordings and session logs are local data (`var/`, gitignored); curated recordings become fixtures and
  golden examples under `specification/examples/`.
- `.env` (gitignored) holds the Claude API key. Never print it or commit it; the agent must run fully
  without it (local-only).

## Acceptance gates

Automated gates need no network: tests mock Ollama and the Claude API, drive the receiver link with the
fake receiver (replayed recordings), and inject the clock. Nothing reaches a receiver or a paid API.

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
- **Degrade, don't crash.** Ollama down → the piece shows raw text only; no API key → local-only, without
  errors; a dropped link reconnects with backoff; a failed model call never kills the listening loop.
- **The glossary is data.** Q-codes, prosigns and abbreviations live in `glossary/` and are rendered into
  the prompts — never hardcoded, never left to model memory.
- **Ukrainian out, originals kept.** Both tiers answer in Ukrainian; call signs, Q-codes and quoted
  original text stay as sent.
- **The cloud tier is bounded.** It runs on its timer only when there is new text, once at session end,
  under the hourly cost cap, with the stable prefix (instructions + glossary) first for prompt caching.
- **Keep decisions pure**: the piece and session cut rules, `cw_chars` decoding, prompt assembly, schema
  validation, the cloud-call scheduling and the cost cap are functions over plain data with an injected
  clock.
- **Everything is logged to the session log** — every character, piece and explanation with timestamps —
  and a log replays to the same text.
- **Secrets stay out**: never print `.env`; the API key never goes into argv, logs, commits or issue
  comments. To check a value is set, test it without echoing it (`grep -q '^ANTHROPIC_API_KEY=.' .env`).

## Contracts

Changing any of these updates ARCHITECTURE.md and the test that pins it, in the same commit:

- the **piece** and **explanation** record shapes (ARCHITECTURE.md §Pieces and sessions), which are also
  the session-log lines;
- the **segmenter rules and thresholds** (end-of-turn prosigns, pause, length cap; session end), with the
  thresholds living in configuration;
- the **local explainer's JSON schema** `{text, about}`;
- the **CLI**: `sruti listen --receiver <host:port> --freq <kHz>`;
- the **KiwiSDR extension messages** sruti sends and reads (the table in ARCHITECTURE.md §The receiver);
- the **two-tier table** (when each tier runs, its inputs, budgets and fallbacks).

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
  connection is opened outward (receiver WebSocket, Ollama on `localhost:11434`, the Claude API).
- Public receivers have few slots; recordings exist so that development and tests don't occupy one.
- The cloud tier costs money: Opus ≈ $0.03 per call under the defaults. The hourly cost cap is not
  optional, and no test or gate ever calls a paid API.
- `kiwiclient`'s license must be checked (v0.1) before the project depends on it.
