---
name: execute-issues
description: Execute one phase's GitHub issues (label vA.B::phase) sequentially in dependency order - implement, run the acceptance gates, get owner confirmation for manual DoD checks, commit, push, close - then write vA.B-execution-report.md.
---

# Skill: Execute GitHub Issues

Execute one phase's GitHub issues sequentially. For each one: implement, validate, commit, push and close.
Then write an execution report.

## Usage

```
/execute-issues <label|phase> [--issue SRUTI-###] [--dry-run]
```

The label is the phase label exactly as it appears on GitHub (`v1.1::phase`). A bare `v1.1` also works.

- `/execute-issues v1.1::phase`: execute every open issue of phase v1.1.
- `/execute-issues v1.1::phase --issue SRUTI-007`: one issue (its dependencies must already be closed).
- `/execute-issues v1.1::phase --dry-run`: show the execution plan without changing anything.

## Instructions

### Step 0: Verify prerequisites

1. **Branch:** note the current branch.
2. **Clean tree:** run `git status`. If the only uncommitted files are this phase's issues file or GitHub
   report under `specification/implementation/`, commit them first (`docs: add vA.B issues`). Any other
   uncommitted change: stop and ask.
3. **GitHub:** `gh` is authenticated and the repo has a remote.
4. **Fetch the open issues:** `gh issue list --label "vA.B::phase" --state open --limit 100`.
5. **Read the phase files:** the issues file `specification/implementation/vA.B-issues.md`, and
   `vA.B-github-report.md` for the `SRUTI-###` → `#number` mapping.
6. **Read the spec:** [specification/ROADMAP.md](../../../specification/ROADMAP.md) §vA.B (Goal, Tasks,
   DoD, Tests), [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) (mechanisms and
   contracts) and [specification/MISSION.md](../../../specification/MISSION.md) (principles and non-goals),
   plus `CLAUDE.md`: the gates and the rules that are easy to break.
7. **Green baseline:** run the automated gates that apply (see `CLAUDE.md` **Acceptance gates**), so a
   later failure can be attributed. Never start on a red suite.

### Step 1: Build the execution queue

- **Order:** parse `SRUTI-###` ids from the issue titles (`SRUTI-###: {title}`) and order them by the issues
  file's Dependency Tree. Issues with no unmet dependency go first.
- **Resuming:** closed issues are already excluded (`--state open`), so a re-run resumes where the last one
  stopped.
- **`--issue`:** execute only that issue, after checking that its dependencies are closed.

Show the plan and ask for confirmation. With `--dry-run`, stop here.

### Step 2: Execute each issue (loop)

#### 2a. Announce

Print `--- Starting SRUTI-###: {title} ---`.

#### 2b. Read the issue

Read its detailed section in the issues file: what needs to be done and the acceptance criteria.

#### 2c. Implement

Follow `CLAUDE.md` and ARCHITECTURE.md. Route by component:

- **`receiver`:** the KiwiSDR link on `kiwiclient` — the audio channel in CW mode at the chosen frequency,
  the `CW_decoder` extension (attach, `cw_start`, `cw_pboff`), `cw_chars` decoding with timestamps, decoder
  status (`cw_wpm`, `cw_train`), reconnect with backoff, and "receiver busy" / "time limit reached" as
  states, not crashes. Listen only: send nothing to the receiver beyond the documented tuning and decoder
  `SET` messages; one connection per run, identified as `sruti`.
- **`segmenter`:** pure logic, characters → pieces → sessions per ARCHITECTURE.md §Pieces and sessions.
  Thresholds come from configuration; the clock is injected.
- **`glossary/`:** versioned data files (Q-codes, prosigns, abbreviations, per-language habits, prefixes)
  rendered into both prompts. Domain knowledge lives here, not in model memory or hardcoded strings.
- **`explain/local`:** per piece — instructions + glossary + the session's last pieces + the new piece →
  Ollama `/api/chat` with a JSON schema → `{text, about}`. 5 s budget; on any failure the piece shows raw
  text only, never a crash.
- **`explain/cloud`:** on a timer (every 3 min), only when the session has new text, and once at session
  end — the whole session → the Claude API. Prompt caching on the stable prefix; the hourly cost cap; on
  screen it supersedes the local explanations it covers; without an API key the agent runs local-only,
  without errors. Scheduling decisions are pure functions with an injected clock.
- **`ui`:** terminal only — raw text streams as characters arrive, L1/L2 under each closed piece, cloud
  explanations as a distinct block. Output language is Ukrainian; call signs, Q-codes and quoted original
  text stay as sent. Unreadable text is `[...]`, never a guess.
- **`log`:** JSONL of every character, piece and explanation with timestamps, matching the record shapes in
  ARCHITECTURE.md; a session log replays to the same text.
- **Contract changes** (CLAUDE.md **Contracts**) update ARCHITECTURE.md and the test that pins the
  contract, in the same commit.
- **`ops` issues** produce their repo artifacts (recordings, golden examples) plus a numbered checklist for
  the owner. Don't connect to a public receiver or call a real model unless the owner asks.
- **Scope:** stay inside the phase; don't add what no phase asks for. Follow the existing style.

#### 2d. Validate

1. **Lint:** `uv run ruff check .` must be clean.
2. **Tests:** `uv run pytest` must exit 0. Every code issue adds or extends tests. Mock Ollama and the
   Claude API, drive the link with the fake receiver; no test touches the network or a paid API.
3. **Manual (owner) criteria:**
   - **Your share:** run whatever can be checked offline from the repo yourself (replays of recorded
     sessions, fixture checks).
   - **The owner's share:** for the rest — live receiver sessions, real Ollama or Claude runs, quality
     judgments against the reference answer — print a numbered checklist and ask the owner to perform and
     confirm it.
   - **Live runs** (a public receiver, a real model, the golden-example eval) happen only when the owner
     asks.
   - **Recording:** record each item as `confirmed by owner` or `pending owner`, never as `pass` on your own.
4. **Acceptance criteria:** walk each criterion against the phase DoD in ROADMAP.md §vA.B.

Gates that don't apply yet (there is no `pyproject.toml` before v1.1) are recorded as `n/a`. Never commit on
a red gate.

#### 2e. Commit

```bash
git add {specific files created or modified}
git commit -m "$(cat <<'EOF'
SRUTI-###: {title}

{1-2 sentence summary of what was implemented}

Closes #{github-issue-number}

Co-Authored-By: <the running model's trailer> <noreply@anthropic.com>
EOF
)"
```

- **Manual checks still pending:** write `Refs #N` instead of `Closes #N`, so that pushing doesn't close an
  issue the owner hasn't verified.
- **`ops` issue with no repo artifact:** it has no commit; go straight to 2g once the owner confirms.

#### 2f. Push

`git push`.

#### 2g. Close or hold the issue

- **All criteria met:** close the issue with a summary.

  ```bash
  gh issue close {number} --comment "$(cat <<'EOF'
  ## Implementation Summary

  **Commit:** {hash or "none (owner steps only)"}
  **Files changed:** {count}

  ### What was done
  {bullets}

  ### Validation
  {lint / tests: pass, fail or n/a; manual: confirmed by owner}

  ### Acceptance criteria
  {checklist}
  EOF
  )"
  ```

- **Owner checks still pending:** leave the issue open. Comment with the pending checklist, mark it
  `awaiting owner` in the log, and continue with issues that don't depend on it.

#### 2h. Log progress

Add to the execution log: the issue id and title, commit, files, gate results, manual checks, and status
(`completed` / `awaiting owner` / `failed` / `skipped`).

### Step 3: Handle failures

If implementation or validation fails:

1. Do not commit broken code.
2. Revert: `git checkout -- .` for tracked files, and delete **by name** the new files this issue created.
   Never `git clean`.
3. Comment on the GitHub issue explaining what failed.
4. Log the failure.
5. Ask the user whether to continue with the next issue (if nothing depends on the failed one) or stop.

### Step 3b: No automatic version bump

Never change `VERSION`, `RELEASE.txt`, `pyproject.toml`'s version or tags here. That is `/release-version`,
on explicit confirmation. A phase with failed, skipped or `awaiting owner` issues is **not** releasable;
say so in the report.

### Step 4: Write the execution report

Write `specification/implementation/vA.B-execution-report.md`:

```markdown
# Phase vA.B — Execution Report

**Date:** {date}
**Branch:** {branch}
**Label:** vA.B::phase
**Target release:** vA.B.0
**Executed by:** Claude Code

## Summary

| Status | Count |
|--------|-------|
| Completed | {n} |
| Awaiting owner | {n} |
| Failed | {n} |
| Skipped | {n} |
| Remaining | {n} |

## Issues

| # | SRUTI ID | Title | Status | Commit | Files | Gates | Manual |
|---|----------|-------|--------|--------|-------|-------|--------|
| 1 | SRUTI-001 | ... | completed | a1b2c3d | 4 | lint ✓ tests ✓ | confirmed |

## Detailed Results

### SRUTI-001: ...
**Status:** completed · **Commit:** a1b2c3d · **GitHub:** #5
**Gates:** [x] lint · [x] tests
**Manual (owner):** {each check: confirmed by owner / pending owner}

## Next Steps
{remaining or awaiting-owner issues, their dependencies, and whether the phase is releasable}
```

Commit the report (`docs: vA.B execution report`, with the trailer) and push.

## Important Rules

- **One issue at a time**, in dependency order. Never start an issue whose dependencies aren't closed.
- **One issue = one commit.** Never mix work across ids.
- **No broken code.** Commit only when the gates that apply are green.
- **Tests ship with the feature.** Ollama and the Claude API are mocked, the fake receiver replays
  recordings, and no test or gate calls the network or a paid API. Live receiver sessions, real model runs
  and the golden-example eval are opt-in, by the owner.
- **Manual checks need the owner.** Never report a manual DoD check as passed without the owner's
  confirmation, and never `Closes #N` an issue with pending owner checks.
- **Contracts stay stable.** A contract change updates ARCHITECTURE.md and its pinning test
  in the same commit.
- **Mission invariants:**
  - **Listen only.** No code path transmits or keys anything; nothing is sent to the receiver beyond the
    documented tuning and decoder `SET` messages.
  - **Never invent.** Unreadable text is `[...]`; a call sign is never "corrected" into a different one.
  - **A polite guest.** One connection per run, identified as `sruti`; back off from busy receivers and
    respect their time limits.
  - **Degrade, don't crash.** No Ollama → raw text only; no API key → local-only; a dropped link reconnects
    with backoff.
- **Secrets stay out:**
  - Never print `.env`. To check that a value is set, test it without echoing it
    (`grep -q '^ANTHROPIC_API_KEY=.' .env`).
  - The API key never goes into argv, logs, commits or issue comments.
- **Ask on ambiguity.** If an issue is unclear, ask rather than guess.
- **Progress updates.** Print a short status line after each issue.
