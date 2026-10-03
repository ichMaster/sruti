---
name: execute-issues-file
description: Execute one phase's issues straight from its local specification/implementation/vA.B-issues.md (no GitHub). Implement -> gates -> owner confirmation for manual checks -> commit -> push (if a remote exists) for each issue in dependency order, then write vA.B-execution-report.md. The offline counterpart of execute-issues.
---

# Skill: Execute Issues From File

Execute one phase's issues **straight from its issues file**, `specification/implementation/vA.B-issues.md`,
with **no GitHub involvement**: no issue lookup and no closing. Each issue is implemented, validated,
committed and pushed in dependency order, and the run ends with an execution report.

This is the offline counterpart of `/execute-issues`. The discipline is the same; only the issue list comes
from the markdown file instead of `gh issue list`.

## Usage

```
/execute-issues-file <vA.B | path-to-issues-file> [--issue SRUTI-###] [--dry-run]
```

- `/execute-issues-file v1.1` → executes `specification/implementation/v1.1-issues.md`.
- `/execute-issues-file @specification/implementation/v1.2-issues.md`.
- `--issue SRUTI-###`: only that issue. Its file-listed dependencies must already be committed.
- `--dry-run`: print the execution plan without changing anything.

## Instructions

### Step 0: Verify prerequisites and read the file

1. **Branch and tree:** note the current branch and check `git status`.
   - If the only uncommitted file is this phase's issues file, commit it first (`docs: add vA.B issues`).
   - Any other uncommitted change: stop and ask.
2. **Remote:** check `git remote -v`. Without a remote, the run commits but doesn't push; say so up front.
3. **Read the issues file:** resolve the target to `specification/implementation/vA.B-issues.md` and read the
   summary table, the Dependency Tree and every `### SRUTI-###` section. **No `gh` is used.**
4. **Read the spec:** [specification/ROADMAP.md](../../../specification/ROADMAP.md) §vA.B (Goal, Tasks, DoD,
   Tests), [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) (contracts) and
   [specification/MISSION.md](../../../specification/MISSION.md) (principles and non-goals), plus
   `CLAUDE.md` (the gates and the rules that are easy to break).
5. **Green baseline:** run the automated gates that apply, so a later failure can be attributed.

### Step 1: Build the execution queue from the file

- **Order:** parse the ids and titles from the summary table and order them by the Dependency Tree.
- **Skip what's done:** an issue whose id already appears in a commit subject (`git log --grep "^SRUTI-###:"`)
  is done; skip it. This is what makes the run resumable.
- **`--issue`:** execute only that issue, after checking that its dependencies are committed.

Show the ordered plan and proceed. With `--dry-run`, stop here.

### Step 2: Execute each issue, in dependency order

1. **Announce:** `--- Starting SRUTI-###: {title} ---`.
2. **Read** its section: what needs to be done and the acceptance criteria.
3. **Implement** per `CLAUDE.md` and ARCHITECTURE.md, routed by component. The routing is the same as
   `/execute-issues` Step 2c:
   - `receiver`: the KiwiSDR link, sruti's own WebSocket client (never `kiwiclient`) — one CW audio
     channel, audio and raw messages as events, reconnect with backoff, busy and time-limit states.
     Listen only; one connection, identified as `sruti`.
   - `decoder`: sruti's own CW decoder, pure — audio in, timestamped characters out; tested on
     synthesized Morse and recorded WAVs.
   - `segmenter`: pure characters → pieces, thresholds from configuration, clock injected; sessions are
     manual, not the segmenter's.
   - `store`: append-only JSONL sessions under `var/sessions/` in ARCHITECTURE.md's record shapes; replay
     to the same text; the manual session switch (retune = new session); past sessions never rewritten.
   - `glossary/`: versioned data rendered into both prompts.
   - `explain/piece`: Gemini 3.8 Flash with a response schema → `{gloss, action, message/rebuilt}` in
     English (sections 2–3), buffered by piece; 5 s budget; running cost summed per session; on failure or
     without a Gemini key raw text only.
   - `explain/session`: Claude Opus 5.5 **only on the Explain action** → a Ukrainian explanation
     (section 4); prompt caching on the stable prefix; per-call cost shown and summed; Explain reports it
     is off without a Claude key.
   - `ui/app`: the pywebview desktop app — the four sections, the config panel with the capture
     inspector, the session switcher; the page talks to the core only through the JS bridge, no port. The
     core never imports the app's code; `[...]` for the unreadable, call signs and Q-codes as sent.
   - `ops` issues produce their repo artifacts (recordings, golden examples) plus a numbered checklist for
     the owner. Don't connect to a public receiver or call a real model unless the owner asks.
   - A **contract change** updates ARCHITECTURE.md and its pinning test in the same commit.
4. **Validate:**
   - `uv run ruff check .` clean and `uv run pytest` green, with the Gemini and Claude APIs mocked and the
     fake receiver for the link.
   - For **Manual (owner)** criteria, run the offline checks (replays, fixtures) yourself and ask the owner
     to perform and confirm the rest (live receivers, real model runs, quality judgments).
   - Record each result as pass / fail / n/a, and each manual check as `confirmed by owner` /
     `pending owner`.
5. **Commit** (one issue = one commit, only when the gates are green):

   ```bash
   git commit -m "$(cat <<'EOF'
   SRUTI-###: {title}

   {1-2 sentence summary of what was implemented}

   Co-Authored-By: <the running model's trailer> <noreply@anthropic.com>
   EOF
   )"
   ```

   There is no `Closes #…` line, since there is no GitHub issue. An `ops` issue with no repo artifact has no
   commit; it is done once the owner confirms.
6. **Push:** `git push` if a remote exists.
7. **Log** the id and title, commit, files, gate results, manual checks and status (`completed` /
   `awaiting owner` / `failed` / `skipped`).

An issue whose code is committed but whose owner checks are pending is `awaiting owner`. Continue with
issues that don't depend on it.

### Step 3: Handle failures

On a failed implementation or a red gate:

1. Don't commit.
2. Revert tracked changes with `git checkout -- .` and delete **by name** the new files this issue created.
   Never `git clean`.
3. Log the failure.
4. Ask whether to continue with the next independent issue or stop.

### Step 3b: No automatic version bump

Never touch `VERSION`, `RELEASE.txt`, `pyproject.toml`'s version or tags here; that is `/release-version`.
A phase with failed, skipped or `awaiting owner` issues is not releasable.

### Step 4: Write the execution report

Write `specification/implementation/vA.B-execution-report.md` with the same structure as `/execute-issues`
Step 4:

- a status summary table;
- a per-issue table (SRUTI id · title · status · commit · files · gates · manual);
- detailed results;
- next steps.

There is no GitHub column. Commit it (`docs: vA.B execution report`, with the trailer) and push if a remote
exists.

## Important Rules

- **File-driven, no GitHub.** The issue list, details and order come from `vA.B-issues.md`. Never run
  `gh issue list`/`create`/`close`, and never write `vA.B-github-report.md`.
- **One issue = one commit**, one issue at a time, in dependency order.
- **No broken code.** Commit only when lint and tests are green.
- **Tests ship with the feature**, with the Gemini and Claude APIs mocked and the fake receiver for the
  link. No test or gate calls the network or a paid API.
- **Manual checks need the owner.** Never report one as passed on your own. Live receivers, real model
  runs and the golden-example eval are opt-in, by the owner.
- **Contracts stay stable**: ARCHITECTURE.md and the pinning test change together.
- **Mission invariants hold**: listen only, never invent (`[...]`, no "corrected" call signs), a polite
  guest, the session tier only on the Explain action, sessions manual and always saved, degrade instead of
  crashing.
- **Secrets stay out.** Never print `.env`; an API key never appears in argv, logs, commits or a URL.
- **Ask on ambiguity.** If an issue's scope is unclear, ask rather than guess.
- **Progress updates.** Print a short status line after each issue.
