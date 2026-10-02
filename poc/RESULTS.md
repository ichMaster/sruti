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
2. **Open (v0.2):** the glossary in the prompt — the full file or the hints file.
3. **Settled by 1:** the 5 s budget holds with a full word-by-word gloss on `gemini-3.8-flash`
   (2.1–3.5 s per piece).
