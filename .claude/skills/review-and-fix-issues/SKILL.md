---
name: review-and-fix-issues
description: Code-review a phase, a component or the current branch, write a criticality-ranked recommendations doc in specification/implementation/, implement the fix-now items with regression tests, then record what was done in the SAME doc. Never releases.
---

# Skill: Review & Fix Issues

One loop over the codebase: **review → recommend → fix → record.**

1. Run a critical code review.
2. Write a single recommendations document that ranks findings by criticality and marks each **FIX NOW**
   or **DEFER →**.
3. Implement the fix-now items with regression tests.
4. **Update that same document in place**, marking what was fixed and adding a "Fixes applied" section.

The recommendations and the results live in **one document**.

This skill fixes only small, in-scope, high-value findings. It **never** bumps the version or cuts a
release (that stays with `/release-version`), and it never pulls deferred or larger work forward without
flagging it.

## Usage

```
/review-and-fix-issues [target]
```

- `/review-and-fix-issues v1.1`: review what the phase delivered (through its tag `v1.1.0` if released).
- `/review-and-fix-issues receiver`: scope the review to one component
  (`receiver` / `segmenter` / `glossary` / `explain` / `ui` / `log` / `tests`).
- `/review-and-fix-issues`: review the **current branch**, i.e. everything built so far.

## Instructions

### Step 0: Scope and a green baseline

1. **Resolve the target:**
   - a phase (`vA.B`) / a version (`vA`) or its tag: the commits whose subjects carry that phase's `SRUTI-###` ids, plus
     the files they touched;
   - a component;
   - no argument: the whole working tree.
2. **Clean tree:** check `git status` is clean and note the branch.
3. **Green baseline:** run the automated gates (`uv run ruff check .`, `uv run pytest`). If the suite is
   **red or flaky**, say so. Fix a clear flake first (small, its own commit) or raise it and ask.
   **Never review or fix on top of a red suite.**

### Step 1: Critical code review

Read the in-scope code and take the highest-risk areas first. Be **adversarial**: hunt for *real*
defects, not restatements of what works.

- **Listen only, a polite guest:**
  - Does any code path send the receiver anything beyond the documented tuning and decoder `SET` messages?
  - Is it one connection per run, identified as `sruti`?
  - Does the link back off from a busy receiver instead of hammering it, respect the time limit, and
    disconnect when idle?
- **Receiver link robustness:**
  - Does a dropped WebSocket reconnect with backoff, and are "busy" and "time limit reached" states rather
    than crashes?
  - Does a reconnect duplicate or lose characters in the session log?
  - Is `cw_chars` URI-decoding safe against malformed input, and are unknown extension messages ignored
    rather than fatal?
  - Is the tone offset (`cw_pboff`) set per ARCHITECTURE.md, so the decoder actually hears the signal?
- **Segmenter:**
  - Do pieces close exactly on the specified rules — an end-of-turn prosign **standing alone** (`K`, `KN`,
    `BK`, `AR`, `SK`), the pause, the length cap — and does a prosign inside a word *not* cut?
  - Do sessions end on `SK`, a frequency change, or the silence threshold?
  - Are the thresholds configuration, not constants, and is the clock injected?
  - Are timing edge cases right (characters straddling the pause boundary, a cut at exactly the cap)?
- **Never invent:**
  - Is unreadable text marked `[...]`, never guessed? Is the decoder's `[err]` handled?
  - Can any prompt or post-processing "correct" a call sign into a different call sign?
  - Is uncertainty surfaced rather than smoothed over?
- **Local explainer:**
  - Is the model output validated against the JSON schema, and does invalid or missing output degrade to
    raw text only — never a crash, never a half-parsed guess?
  - Is Ollama being down or slow handled within the 5 s budget?
  - Does the prompt carry the glossary, the last pieces and the new piece as specified?
  - Is the output Ukrainian with call signs, Q-codes and quoted original text kept as sent?
- **Cloud explainer:**
  - Does it fire only on the timer **when there is new text**, and once at session end?
  - Does a missing API key mean local-only operation with no errors?
  - Is the hourly cost cap enforced, and counted correctly across sessions?
  - Is the stable prefix (instructions + glossary) first, so prompt caching works?
  - Are the scheduling decisions pure functions with an injected clock?
  - Can a failed or slow Claude call kill the listening loop? Does the display block correctly supersede
    the local explanations it covers?
- **Session log:**
  - Is every character, piece and explanation logged with timestamps, in the record shapes of
    ARCHITECTURE.md §Pieces and sessions?
  - Does a log replay to the same text, and does a crash mid-write corrupt the log?
- **Robustness:**
  - Can an exception in the character callback or an explainer call kill the listening loop?
  - Are empty and huge pieces handled, and what happens when the models are slower than the stream
    (backpressure)?
- **Secrets and costs:**
  - Does the API key appear in logs, exception messages, argv or `repr`?
  - Does any test or gate call the network or a paid API? Are the eval and live checks opt-in only?
- **Spec drift:** does the code diverge from the ARCHITECTURE.md contracts or the ROADMAP, or add what no
  phase asks for (MISSION.md non-goals: transmitting, digital modes, voice, logging/QSL, a GUI in v1)?

For each finding, capture:

- a **concrete failure scenario** (inputs → wrong result or crash);
- a `file:line` anchor;
- a **severity**: 🔴 HIGH / 🟠 MEDIUM / 🟡 LOW;
- a **proposed fix**.

Cross-check against ROADMAP.md and ARCHITECTURE.md. If a gap is already scheduled for a later phase (e.g.
local decoding is v2), note that instead of treating it as new.

### Step 2: Write the recommendations document (the plan)

Write **one** doc at `specification/implementation/<scope>-code-review.md`, e.g. `v1.1-code-review.md`,
`receiver-code-review.md`, or `branch-code-review.md` for the whole tree. Include:

- a header: date, reviewer, **scope**, method;
- a **criticality-ranked summary table**: `# | Severity | Finding | Recommendation | Status`.
  Recommendation is `FIX NOW` or `DEFER → <home>`; Status starts as `⏳ pending`;
- for each finding, its failure scenario and proposed fix;
- a short **"What's solid"** section, to keep the review balanced;
- **suggested next actions**.

Decide **FIX NOW vs DEFER** honestly:

- **FIX NOW** means real, small, self-contained, high-value and in scope now: a crash that kills the
  listening loop, an invented call sign, a hammered receiver, the API key in a log, a session log that
  doesn't replay.
- **DEFER →** means larger work, or work a later phase already owns. Give the home: a later phase
  (`v1.2`…`v1.4`, `v2`, `v3`), `backlog` (no phase owns it) or `cleanup (/simplify)`. Do **not** pull it
  forward.

Commit the doc as the plan (`docs: vA.B code review`) **and push it** if a remote exists. The review is worth
keeping even if the fix pass is interrupted.

### Step 3: Implement the FIX NOW items, with tests

For each **FIX NOW** finding, in criticality order:

1. Implement the fix following `CLAUDE.md` and ARCHITECTURE.md. Keep it minimal.
2. **Add a regression test that would have caught the bug**, with Ollama and the Claude API mocked and the
   fake receiver for the link. For a timing bug, drive the injected clock explicitly.
3. **Validate:** lint and tests green. Commit only passing code.
4. **Commit** one focused change per finding: `fix(<area>): … (code review #N)`, with the running model's
   `Co-Authored-By` trailer. **Then push.** Never leave a landed fix unpushed.
5. **A contract change** updates ARCHITECTURE.md and the pinning test in the **same** commit.

If a fix turns out bigger than "fix now" (it touches a contract broadly or needs a design decision),
**stop and re-classify it as DEFER** in the doc, with the reason, and move on. Don't half-land it.

### Step 4: Update the SAME document (the result)

Edit the doc **in place**:

- **Status column:** flip it to `✅ FIXED — <commit>` for each applied fix; keep `⏳ deferred` for the rest.
- **"Fixes applied" section:** for each fix, give the change, the regression test and the verification
  (final gate status).
- **"Architecture impact" note:** add one for any fix that **changed a documented contract or
  design-relevant behavior**, and make sure ARCHITECTURE.md reflects it. The next
  `/generate-issues` or `/reconcile-issues` reads these notes.
- **"Suggested next actions":** update them. Fixes on an already-released phase suggest a patch release
  (`/release-version A.B.1`); deferred items are carried into their phase.

Commit the update (`docs: vA.B code review — fixes applied`) **and push**.

### Step 5: Report

Summarize:

- findings by severity;
- which were **fixed** (with commits) and which **deferred** (with homes);
- the final gate status.

If fixes landed on an already-released phase, suggest `/release-version A.B.<next>`, but do **not** run
it. Offer a deeper pass with `/code-review high` for confirmation.

## Important Rules

- **One document, updated in place.** Recommendations and results share a single doc.
- **Fix only the FIX NOW items.** Never pull deferred work forward without re-classifying it in the doc.
- **Every fix ships a regression test**, with the models mocked. No test calls the network or a paid API.
- **Green before, green after.** Commit only code that passes the gates.
- **Record architecture deltas.** A contract change updates ARCHITECTURE.md and its test in
  the same commit, and gets an "Architecture impact" note.
- **Never release.** No version bump, no tag.
- **Never leave work unpushed** (when a remote exists). This skill can stop mid-way, so "the next step will
  push it" is not a safe assumption.
- **Ask on genuine ambiguity**: an unclear scope, or a borderline fix-now-vs-defer call.
