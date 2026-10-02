# Architecture — sruti

## Overview

```
Public KiwiSDR (receiver + its CW decoder)
   ⇅  WebSocket opened from the Mac — audio channel (SND) + CW_decoder extension (EXT)
sruti on the Mac (Python)
   receiver link → segmenter → local explainer (Ollama, localhost) → terminal
                        └────→ cloud explainer (Claude API, every few minutes) → terminal
```

One process, one receiver, one frequency at a time. Data flows one way — characters → pieces → explanations → screen — and every step is also written to a session log.

## Components

1. **Receiver link (`receiver`).** Opens an audio channel on the chosen KiwiSDR in CW mode at the chosen frequency, attaches the receiver's `CW_decoder` extension, starts it, and emits decoded characters with timestamps plus decoder status (speed, training). Reconnects with backoff; "receiver busy" and "time limit reached" are states, not crashes. Built on `kiwiclient`.
2. **Segmenter (`segmenter`).** Pure logic: characters → pieces → sessions (§Pieces and sessions).
3. **Glossary (`glossary/`).** Versioned data: Q-codes, prosigns, common abbreviations, per-language CW habits (Italian `ET` for "and", `CAMBIO` for "over"), call-sign prefixes. Rendered into both prompts.
4. **Local explainer (`explain/local`).** Per piece: instructions + glossary + the session's last pieces + the new piece → Ollama `/api/chat` with a JSON schema → `{text, about}` (L1, L2).
5. **Cloud explainer (`explain/cloud`).** On a timer, only when the session has new text, and once when a session ends: the whole session → Claude → a full explanation in the style of the reference answer. On screen it supersedes the local explanations it covers.
6. **Display (`ui`).** Terminal. Raw text streams as characters arrive; each closed piece gets its L1/L2 lines underneath; cloud explanations appear as a distinct block.
7. **Session log (`log`).** JSONL of every character, piece and explanation with timestamps — the source of replays, test fixtures and new golden examples.

## The receiver

**Why KiwiSDR.** websdr.org receivers only work in a browser. KiwiSDR has an open WebSocket protocol, a maintained Python client ([jks-prv/kiwiclient](https://github.com/jks-prv/kiwiclient)) and a public directory of about 870 receivers with load, bands and location (`kiwisdr.com/public`). **Verified** from the Mac: a public KiwiSDR (Heppen, Belgium) connects through the endpoint filtering, and audio arrives as 12 kHz mono 16-bit.

**Its CW decoder.** The KiwiSDR decodes CW on the receiver (`extensions/CW_decoder`, a Goertzel decoder derived from UHSDR) and sends the text to the client. The protocol below is read from the KiwiSDR source and **not yet exercised end to end** (v0.1):

| Direction | Message | Meaning |
|---|---|---|
| → | `SET ext_switch_to_client=CW_decoder first_time=1 rx_chan=0` | attach the extension to this connection's channel |
| → | `SET cw_start=<training>` | start decoding; `<training>` is how much signal is used to learn the speed (browser default 100) |
| → | `SET cw_pboff=<Hz>` | the audio tone the decoder listens on: passband centre − carrier |
| → | `SET cw_wpm=<wpm>,<training>` | fixed speed; `0` = automatic |
| → | `SET cw_auto_thresh=0\|1`, `SET cw_threshold=<linear>` | signal threshold (browser default: fixed, 47 dB) |
| → | `SET cw_wsc=0\|1` | word-space correction |
| → | `SET cw_stop` | stop decoding |
| ← | `cw_chars=<URI-encoded text>` | decoded characters; prosigns as strings, unknown codes as `[err]` |
| ← | `cw_wpm=<n>` | current estimated speed |
| ← | `cw_train=<n>` | training progress; negative = error count |
| ← | `cw_plot=<dB>,<polarity>,<threshold>` | signal level (ignored) |

**Frequency and tone.** In CW mode the default passband is 300–700 Hz above the carrier. `kiwiclient` treats the frequency as the carrier unless `--pbc` makes it the passband centre. Spots and band plans give the signal's frequency, so sruti tunes with the given frequency at the passband centre. **Open:** with `--pbc`, the beacon on exactly 14.100 MHz came out as a ~1003 Hz tone, not the expected 500 Hz. The decoder only hears the tone at `cw_pboff`, so v0.1 establishes the true offset before anything depends on it.

**Being a guest.** One connection per run, identified as `sruti`. Public receivers limit slots and session time; the link reports both and backs off from a busy receiver.

## Pieces and sessions

- A **piece** closes on an end-of-turn prosign standing alone (`K`, `KN`, `BK`, `AR`, `SK`), on 3 s without characters, or at 200 characters.
- A **session** ends on `SK`, a frequency change, or 60 s without characters.
- The thresholds are configuration; these values are starting points, tuned on recorded sessions.

Records — also the session-log lines:

```
piece        {session, seq, receiver, freq_khz, wpm, t_start, t_end, cut: prosign|pause|length, raw}
explanation  {session, piece_seq | null, tier: local|cloud, model, text, about, latency_ms}
```

## The two tiers

| | Local tier | Cloud tier |
|---|---|---|
| When | every piece | every 3 min if there is new text, and at session end |
| Input | glossary + last 5 pieces + the new piece | glossary + the whole session |
| Output | JSON `{text, about}` — L1 and L2 | a full explanation, reference-answer style |
| Where | Ollama on the Mac, `localhost:11434` | Claude API |
| Budget | ≤ 5 s after the piece closes | ≤ 30 s; an hourly cost cap |
| When unavailable | the piece shows raw text only | the agent carries on with the local tier |

**Output language** is Ukrainian for both tiers. Call signs, Q-codes and quoted original text stay as sent.

**Local model — not chosen yet.** It must restore CW text in the operators' language (English, Italian, German…), translate it into natural Ukrainian, follow a JSON schema, fit in 32 GB next to other apps, and meet the 5 s budget. Measured so far:

| Model | Result on example 001 | Speed on the Mac |
|---|---|---|
| `qwen3:8b`, thinking off | **Fails.** L1 echoed the Italian instead of translating; L2 read `IU3 F E JDE` as one call sign and "il grande Lino" as "a great line". | 20 tok/s; 14 s warm, 24 s cold |

Next candidates, available in Ollama and untested: `gemma4:12b` (the strongest multilingual line), `qwen3.5:9b`. The choice is made in v0.2 against the golden examples.

**Cloud model.** Claude Opus 5.5 (`claude-opus-5-5`, $4 / $20 per million input / output tokens) by default, at low effort; Claude Fable 5.1 (`claude-fable-5-1`, $10 / $50) by configuration. At an estimated ~3K input and ~1K output tokens per call: Opus ≈ $0.03 per call, about $0.6 per hour of continuous traffic; Fable ≈ $0.08 per call, about $1.6 per hour. Instructions and glossary form a stable prefix for prompt caching.

## Hosts

- **The Mac** (M1 Pro, 32 GB, managed): runs everything; Ollama is installed. Constraints: no SDR software, inbound connections destroyed by endpoint filtering, outbound HTTPS and WebSocket work.
- **`ich-picobox`** (Ubuntu 22.04, x86-64, 4 cores, 15 GB, no GPU, on the LAN): not used in v1. A possible later home for the receiver link or own SDR hardware; too weak for the local model.

## Testing

- **Unit** — segmenter rules, `cw_chars` decoding, glossary rendering, prompt assembly, output-schema validation.
- **Fake receiver** — replays recorded extension messages from session logs, so the whole pipeline runs without a network.
- **Models are mocked by default.** No test calls Ollama or the Claude API unless asked to.
- **Golden-example eval** (opt-in) — runs a real model over `specification/examples/`, records quality notes and latency; the basis of every model and prompt choice.
- **Live check** (opt-in) — the NCDXF/IARU beacons on 14.100 MHz send known call signs at 22 WPM on a 3-minute cycle: a real signal with a known answer.
