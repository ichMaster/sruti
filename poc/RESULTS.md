# PoC results — the explainer on example 001

**Date:** 2026-10-02 · **Script:** [explain_piece.py](explain_piece.py) · **Input:** the three decoder
blocks of [example 001](../specification/examples/001-italian-ragchew.md) fed as three pieces, with the
section-3 state carried between calls · **Contract:** `{gloss, action, message/rebuilt}`.

These are experiment notes. Nothing here changes the specification until the owner decides.

## All runs

| Model | Where | Glossary | Time per piece | Quality |
|---|---|---|---|---|
| `qwen3:8b`, thinking off (earlier run, two-field schema, before this PoC) | local | none | 14 s warm, 24 s cold | Fails. Echoed the Italian instead of translating; read `IU3 F E JDE` as one call sign and "il grande Lino" as "a great line". |
| `qwen3:8b`, thinking off | local | full | 29–33 s | Weak. The message is a word-salad echo; cut numbers applied inside ordinary words. |
| `qwen3.5:9b` | local | full | 34–48 s | Good messages; piece 3 near the reference. Some guesses not marked (`UAI` → "you hear me"); `RIP ASS O` read as three tokens. |
| `qwen3.5:9b` | local | none | 19–45 s | Wrong on CW tokens: `HW` → "hands free", `R` → "read me", `K` → "acknowledge". Invents a prosign for a stray `T`; piece 1 left untranslated. |
| `gemini-2.5-flash`, thinking off | cloud | full | 2.3–3.6 s | Clean messages, CW tokens right. Marked plain Italian words as unknown (the prompt's "ONLY the glossary" rule), so it lost the handover and "not long in CW". |
| `gemini-2.5-flash`, thinking off | cloud | none | 2.2–3.8 s | `CAMBIO` → "I change"; invents a reading of the unreadable start; messages turn into word salad. |
| `gemini-3.1-pro-preview`, thinking low | cloud | none | 6.2–10.8 s | Reference substance with no glossary. Rejoins split words, repairs letters, flags `INFTA` as uncertain. Merges `IU3 F E JDE` into `IU3FEJ` without a flag. |
| **`gemini-3.8-flash`, thinking low** | cloud | **hints** | **2.1–3.5 s** | **Best.** Reference substance; flags its own merge (`IU3FEJ (?)`); joins the thought across pieces ("not long… that I have been doing CW"); shows each reconstruction in the gloss. |
| `gemini-3.8-flash`, thinking low | cloud | none | 2.1–3.2 s | Good, but loses "you don't know… not long" and merges `IU3FEJ` without a flag. |

**Glossary modes:** full = [glossary/cw.md](../glossary/cw.md) (5.8K characters, every abbreviation);
hints = [glossary/cw-hints.md](../glossary/cw-hints.md) (1.7K characters, only what models get wrong:
decoder damage, misread habits, call-sign rules); none = no glossary.

## Where the local time goes (`qwen3.5:9b`, full glossary)

| Step | Piece 1 (cold) | Piece 2 | Piece 3 |
|---|---|---|---|
| Model load | 26.3 s | 0 | 0 |
| Prompt read (~2.4K tokens) | 11.0 s | 5.1 s | 5.2 s |
| Generation | 356 tok, 17.2 s | 1006 tok, 48.4 s | 707 tok, 35.5 s |

Generation runs at ~20 tokens per second on the M1 Pro, so the length of the answer sets the time. The
prompt is re-read in full on every call, which suggests Ollama's prefix cache is not being reused; not yet
investigated.

## Prices

From [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing), fetched
2026-10-02, standard paid tier, per million tokens. Thinking tokens are billed as output. The per-piece
cost uses the token counts measured in the runs above; the per-hour cost assumes ~100 pieces per hour of
lively conversation.

| Model | Input | Output | Tokens per piece (in / out) | Per piece | Per hour |
|---|---|---|---|---|---|
| `gemini-2.5-flash` | $0.30 | $2.50 | ~2,370 / ~490 (full glossary) | ~$0.002 | ~$0.20 |
| `gemini-3.1-pro-preview` | $2.00 | $12.00 | ~480 / ~960 incl. ~355 thinking (no glossary) | ~$0.013 | ~$1.25 |
| `gemini-3.8-flash` | $0.75 until 2026-12-31, then $1.50 | $3.75 until 2026-12-31, then $7.50 | ~1,060 / ~560 (hints) | ~$0.003 (from 2027 ~$0.006) | ~$0.29 (from 2027 ~$0.58) |

Output is the larger part of the bill for all three. Context caching ($0.03 / $0.20 / $0.075 per
million cached tokens) would cut only the smaller input part.

## Findings

- The local model on this Mac misses the 5 s budget by 7–10×, and the cause is answer length, not the
  glossary.
- A fast cloud model fits the budget: 2–4 s per piece.
- The glossary matters for small and mid models. A strong model does without it; the short hints file
  still made `gemini-3.8-flash` better.
- The prompt rule "expand tokens ONLY against the glossary" is too strict: plain words in the operators'
  language must be translated normally.

## Questions for the specification

1. **Decided (2026-10-02):** sections 2–3 run on `gemini-3.8-flash`; the local model is dropped from the
   specification. Section 4 stays on Claude Opus 5.5.
2. **Decided (v0.2, 2026-10-04):** the hints file. See §v0.2 below.
3. **Settled by 1:** the 5 s budget holds with a full word-by-word gloss on `gemini-3.8-flash`
   (2.1–3.5 s per piece).

## v0.2 — the golden examples

**Date:** 2026-10-04 · **Script:** [eval_golden.py](eval_golden.py) · **Input:** the golden examples
001 (Italian ragchew, 3 pieces), 002 (DJ0YI's POTA activation, 6) and 003 (E72U's contest run, 6) ·
**Model:** `gemini-3.8-flash`, thinking low · **Reports:** [eval/](eval/), with the raw answers as JSON
(re-scored offline with `--rescore`).

| Run | Glossary | Prompt | Pieces passing the checks | Latency per piece | Tokens in / out per piece | Cost per piece |
|---|---|---|---|---|---|---|
| 17:30 | hints | PoC prompt; glossary without contest/POTA | 13 / 15 (14 without the checker's false alarms) | 1.5–3.9 s | 1,110 / 390 | $0.0023 |
| 17:30 | full | the same | 13 / 15 (14 without the checker's false alarms) | 1.4–4.1 s | 2,430 / 410 | $0.0034 |
| 17:33 | hints | + "never offer a call sign not in the text"; contest/POTA in both glossaries | 15 / 15 | 1.4–3.6 s | 1,400 / 390 | $0.0025 |
| 17:33 | full | the same | 14 / 15 | 1.6–4.6 s | 2,750 / 470 | $0.0039 |
| **17:38** | **hints** | **+ rebuild that changes nothing is `none`; `(?)` kept in the message** | **15 / 15** | **1.5–4.1 s** | **1,440 / 410** | **$0.0026** |

The checks are: the schema; the 5 s budget; every raw token glossed; no call sign that the raw text lacks;
unreadable text not glossed as certain. The 17:30 runs surfaced false alarms in the checker ("[dits]",
"corrupted text", "OM3CPF/OM3CNF" read as one call sign; "garble" at 17:33). They were fixed before the
decision, and the runs that saved their answers (17:33, 17:38) are re-scored. The 17:30 runs predate
saving and show their raw score.

### What the runs showed

- **Misses the glossary fixed.** In the first run the model offered a call sign absent from the text
  (`UR3WU?` beside `UW3WU`), and the full-glossary run read stray letters as cut numbers (`A` → 1,
  `T` → 0). Adding contest and POTA conventions (`TEST`, serials in cut numbers, `TU`, `CQ POTA`, `/P`,
  `NR?`, `CALL?`) and "a lone letter between exchanges is a fragment" fixed both in the hints run. The
  full run kept reading `A`/`T` as digits.
- **A reference error the model caught.** 002's reference read `RST 5 5N` as 599. The model read 559, and
  it is right: N (`-.`) never decodes as 5 (`.....`), so `5 5N` is 5-5-N = 559. The reference was
  corrected (and `NDE<AS>`, marked wholly unreadable, now reads `DE … <AS>`, as the model did).
- **Quality against the bar.** 001's message carries the reference substance: the IC-7300, the
  handover, the thanks, new to CW, taught by Lino. `IU3FEJ(?)` keeps its mark once the prompt asks for
  it. 002 reads the POTA call, the answer from OK7DA/P (?) and the 559 report, and marks the weak station.
  003 attributes every exchange correctly (`E72U to SP1AEN: 599 057; SP1AEN replies 599 616 TRC`) and
  reads every serial.
- **`rebuild`.** Chosen in 1–2 of 15 pieces per run, always in 002 when `DP 0YE` and `DJ0YI` turned out
  to be one station — the case ARCHITECTURE §The four sections names. Once it rebuilt to the same text,
  which the final prompt calls `none`.

### Decision

The **hints file** (`glossary/cw-hints.md`) and the prompt of [explain_piece.py](explain_piece.py), as
written into ARCHITECTURE §The two tiers. Quality first: the hints and full runs are equal on substance,
and the hints run follows the fragment rule that the full run broke. Then cost and latency: half the
input tokens, ≈ $0.0026 per piece, under 4.1 s.

