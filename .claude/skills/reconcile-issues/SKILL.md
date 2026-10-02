---
name: reconcile-issues
description: Review one phase's already-generated specification/implementation/vA.B-issues.md against the REAL current implementation (and the repo's recordings and reports) and correct any issue that has drifted - stale file names, changed signatures, evolved contracts, or work already done. Edits the file in place with a visible "Reconciled" mark. Corrects issues only; never implements code or changes the version.
---

# Skill: Reconcile Issues

`/generate-issues` grounds new issues in the real implementation (its Step 0.5). This skill does the same
for a **pre-generated** issues file. It reads `specification/implementation/vA.B-issues.md`, compares each
issue's assumptions with the **actual current code**, and **corrects the issues that drifted, in the file,
with a visible change-mark**, so the record shows the original issue was modified.

It only **corrects the issues**: it never implements code, never touches the version and never uses GitHub.
Run it right before `/execute-issues-file`.

## Usage

```
/reconcile-issues <vA.B | path-to-issues-file>
```

- `/reconcile-issues v1.2` → reconciles `specification/implementation/v1.2-issues.md`

## Instructions

### Step 0: Read the issues and the real implementation

1. **The issues file:** resolve the target to `specification/implementation/vA.B-issues.md` and read all of it:
   the summary table, the dependency tree and every `### SRUTI-###` section.
2. **The code:** read the **real current code** the issues touch: the Python package (receiver, segmenter,
   glossary, explain, ui, log modules), `tests/`, `pyproject.toml`, `.env.example` and the glossary data
   files. Note the actual module and function names, signatures, config keys, env var names and
   dependencies.
3. **Earlier records:** read the earlier phases' `specification/implementation/*-execution-report.md` and
   `*code-review*.md`, especially **"Fixes applied"** and **"Architecture impact"**.
4. **The spec:** read [specification/ROADMAP.md](../../../specification/ROADMAP.md) §vA.B (the DoD),
   [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) (contracts) and `CLAUDE.md`.
5. **Owner-run work:** check what can be checked offline — whether the recordings, fixtures or golden
   examples an issue assumes already exist in the repo. If an owner step (a live session, a model eval) may
   already be done, ask the owner. Never connect to a receiver or call a real model yourself.

### Step 1: Find the drift

Compare each issue's **assumptions** with reality:

- **Paths:** wrong or renamed files and modules (e.g. an issue naming `sruti/decoder.py` when the code has
  `sruti/receiver.py`).
- **Names and signatures** that changed: functions, config keys (e.g. a segmenter threshold read from the
  config file vs `.env`), the session-log record fields, the Ollama request shape, the Claude API call
  shape, CLI flags.
- **Contracts** that a landed fix moved past the spec: the piece cut rules, the record shapes, the local
  explainer's JSON schema, the cloud scheduling rules, the `cw_pboff` handling.
- **Work already done:** the deliverable was already shipped by an earlier fix or phase, or an owner step
  (a recording, a model decision) was already performed.
- **The code is ground truth** where it disagrees with the issue text or a stale spec.

### Step 2: Correct the issues in place, with a visible mark

For each issue that drifted, edit its section in `vA.B-issues.md`:

1. **Fix the details** (Description, What needs to be done, Acceptance criteria) so they match the real
   implementation. Keep the **SRUTI id and the intent**; correct only what drifted.
2. **Add a change-mark** as a blockquote directly under the issue heading:
   > **⟳ Reconciled (<today>):** originally referenced `sruti/decoder.py` and a `pause_s` TOML key; corrected
   > to the shipped `sruti/segmenter.py` reading `PIECE_PAUSE_S` from the config. Reason: matches the real
   > implementation.
3. **Moot issues** (already delivered) stay in the file with a clear mark:
   > **⟳ Reconciled (<today>):** already satisfied by `<commit / release / owner step>`; execution is
   > verification-only (add or confirm the test, or re-run the DoD check; no new production code).
4. Use today's date. Never rewrite silently; every change is stamped.

### Step 3: If nothing drifted

Leave issues that match reality untouched. If **no** issue needed a correction, add one note under the
file's intro and stop:
`> **⟳ Reconciled (<today>): no drift found — issues match the current implementation.**`

### Step 4: Record

Commit the corrected file (`docs: reconcile vA.B issues against the implementation`, with the running model's
`Co-Authored-By` trailer) and push if a remote exists. Report which issues were corrected and why, which
were marked moot, and which were untouched.

## Important Rules

- **Correct issues only.** Never implement code, change the version or use GitHub. That is
  `/execute-issues-file` and `/release-version`.
- **The real code is ground truth** where it disagrees with the issue or a stale spec.
- **Every change is marked.** Keep the SRUTI id and intent, and add a dated `⟳ Reconciled` blockquote.
- **No churn.** Don't touch issues that already match reality.
- **Ask on genuine ambiguity.** If it's unclear whether the issue or the code is right, raise it with the
  user rather than guessing.
