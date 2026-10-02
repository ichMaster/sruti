# Architecture — sruti

## Overview

```
Public KiwiSDR (receiver + its CW decoder)
   ⇅  WebSocket opened from the Mac — audio channel (SND) + CW_decoder extension (EXT)
sruti core on the Mac (Python)
   receiver link → segmenter → session store
         │              ├→ local explainer (Ollama, per piece)
         │              └→ cloud explainer (Claude API, on the Explain action)
         └→ core event stream → interface: TUI (v1) · web on localhost (v2)
```

One process, one receiver, one frequency at a time. Data flows one way — characters → pieces →
explanations — every step is appended to the session store, and the interface renders what the core
emits.

## Core and interfaces

The core is UI-agnostic. Components talk through an in-process **event stream** (an asyncio queue): the
receiver emits characters, decoder status and link states; the segmenter emits pieces; the explainers emit
explanations; the store persists everything it sees. An interface subscribes to the stream and sends back
a small, fixed set of **commands**: `tune` (receiver, frequency — which also switches the session),
`start`/`stop`, `explain` (the section-4 button), `open-session`, `set-config`.

Two interfaces, one core, the same events and commands:

- **TUI (v1)** — a [Textual](https://textual.textualize.io) app in the terminal. The four sections
  (§The four sections), the config panel and the session switcher are screens of one app.
- **Web (v2)** — a FastAPI app bound to `127.0.0.1` **only**. The event stream reaches the browser over a
  WebSocket; commands come back as HTTP POSTs; one static page (no build step) renders the same four
  sections, config panel and session switcher. Binding to localhost keeps the managed Mac's constraint —
  nothing listens on the LAN, the browser and the server are the same machine, and every external
  connection is still opened outward. The TUI remains after v2; the interface is chosen at launch
  (`sruti tui` / `sruti web`).

Everything below the interface line — receiver, segmenter, store, explainers, glossary — is identical in
both versions and never imports interface code.

## Components

1. **Receiver link (`receiver`).** Opens an audio channel on the chosen KiwiSDR in CW mode at the chosen
   frequency, attaches the receiver's `CW_decoder` extension, starts it, and emits decoded characters with
   timestamps plus decoder status (speed, training). Reconnects with backoff; "receiver busy" and "time
   limit reached" are states, not crashes. Built on `kiwiclient`. Also emits the **raw extension
   messages** as events, so the config panel's capture inspector can show exactly what arrives from the
   receiver's API.
2. **Segmenter (`segmenter`).** Pure logic: characters → pieces (§Pieces and sessions). It does not cut
   sessions; sessions are manual.
3. **Session store (`store`).** One JSONL file per session under `var/sessions/`, append-only: every
   character, piece and explanation with timestamps. The source of replays, test fixtures and new golden
   examples. Lists saved sessions and replays one into the event stream, read-only.
4. **Glossary (`glossary/`).** Versioned data: Q-codes, prosigns, common abbreviations, per-language CW
   habits (Italian `ET` for "and", `CAMBIO` for "over"), call-sign prefixes. Rendered into both prompts.
5. **Local explainer (`explain/local`).** Per piece — buffered by the segmenter, never word by word as it
   arrives: instructions + glossary + the session's last pieces + the new piece → Ollama `/api/chat` with
   a JSON schema → `{gloss, message}`. `gloss` maps the raw text token by token (word, abbreviation,
   Q-code, prosign, call sign → its expansion and meaning); `message` is the restored text assembled into
   a natural translation. They fill sections 2 and 3.
6. **Cloud explainer (`explain/cloud`).** Only when the user triggers **Explain**: the whole session →
   Claude → a full explanation of what is going on, in the style of the reference answer. Never on a
   timer, never automatic. It fills section 4.
7. **Interfaces (`ui/tui`, later `ui/web`).** §Core and interfaces, §The four sections, §Configuration.

## The receiver

**Why KiwiSDR.** websdr.org receivers only work in a browser. KiwiSDR has an open WebSocket protocol, a
maintained Python client ([jks-prv/kiwiclient](https://github.com/jks-prv/kiwiclient)) and a public
directory of about 870 receivers with load, bands and location (`kiwisdr.com/public`). **Verified** from
the Mac: a public KiwiSDR (Heppen, Belgium) connects through the endpoint filtering, and audio arrives as
12 kHz mono 16-bit.

**Its CW decoder.** The KiwiSDR decodes CW on the receiver (`extensions/CW_decoder`, a Goertzel decoder
derived from UHSDR) and sends the text to the client. The protocol below is read from the KiwiSDR source
and **not yet exercised end to end** (v0.1):

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

**Frequency and tone.** In CW mode the default passband is 300–700 Hz above the carrier. `kiwiclient`
treats the frequency as the carrier unless `--pbc` makes it the passband centre. Spots and band plans give
the signal's frequency, so sruti tunes with the given frequency at the passband centre. **Open:** with
`--pbc`, the beacon on exactly 14.100 MHz came out as a ~1003 Hz tone, not the expected 500 Hz. The
decoder only hears the tone at `cw_pboff`, so v0.1 establishes the true offset before anything depends on
it.

**Being a guest.** One connection per run, identified as `sruti`. Public receivers limit slots and session
time; the link reports both and backs off from a busy receiver.

## The four sections

The display contract, identical in the TUI (v1) and the web page (v2):

| # | Section | Content | Source | When it updates |
|---|---|---|---|---|
| 1 | **Original text** | the decoded characters, as sent | the receiver's decoder (WebSDR) | live, character by character |
| 2 | **Word by word** | each token of the piece → its expansion and meaning | local explainer `gloss` | when a piece closes |
| 3 | **Message** | the piece restored and translated into natural text | local explainer `message` | together with section 2 |
| 4 | **What is going on** | who talks to whom, what kind of exchange, the story so far | cloud explainer (Claude Opus 5.5) | **only when the user presses Explain** |

Sections 2 and 3 come from one local call per piece: the gloss shows *how* the raw text maps to meaning,
token by token; the message is the final readable translation built from it. The local tier runs in near
real time, but on the segmenter's buffer (the piece), never on each word as it arrives. Section 4 is
whole-session and on demand; while a cloud call is running, section 4 says so, and a failed call leaves
the previous explanation with an error note.

**Output languages:** sections 2 and 3 (the local tier) are in **English**; section 4 (the Opus
explanation) is in **Ukrainian**. Both are configuration (`language.local = "en"`,
`language.cloud = "uk"` by default). Call signs, Q-codes and quoted original text stay as sent in every
section.

## Pieces and sessions

- A **piece** closes on an end-of-turn prosign standing alone (`K`, `KN`, `BK`, `AR`, `SK`), on 3 s
  without characters, or at 200 characters. The piece is the local tier's buffer.
- A **session is manual.** It begins when listening starts and ends only when the user switches or quits.
  **Switching the session and retuning are the same action:** changing frequency or receiver closes the
  current session file and opens a new one. `SK` and long silence close pieces and are shown as lulls, but
  never end a session on their own.
- **Every session is saved** — `var/sessions/<started>-<receiver>-<freq>.jsonl`, append-only. The session
  switcher lists them; an opened past session replays into the same four sections, read-only.
- The piece thresholds are configuration; these values are starting points, tuned on recorded sessions.

Records — also the session-store lines:

```
char         {session, t, ch}
piece        {session, seq, receiver, freq_khz, wpm, t_start, t_end, cut: prosign|pause|length, raw}
explanation  {session, tier: "local", piece_seq, model, gloss: [[token, meaning], …], message, latency_ms}
explanation  {session, tier: "cloud", upto_seq, model, text, latency_ms, cost_usd}
```

## The two tiers

| | Local tier | Cloud tier |
|---|---|---|
| When | every piece — buffered, never word by word | **only on the user's Explain action**; never on a timer, never automatic |
| Input | glossary + the session's last 5 pieces + the new piece | glossary + the whole session |
| Output | JSON `{gloss, message}`, in English → sections 2 and 3 | a full explanation in Ukrainian, reference-answer style → section 4 |
| Where | Ollama on the Mac, `localhost:11434` | Claude API |
| Budget | ≤ 5 s after the piece closes | ≤ 30 s per press; every call's cost is shown and summed per session |
| When unavailable | the piece shows raw text only (sections 2–3 stay empty for it) | Explain reports the cloud tier is off; everything else works |

**Local model — not chosen yet.** It must restore CW text in the operators' language (English, Italian,
German…), gloss it token by token, translate the message into natural English, follow a JSON schema, fit
in 32 GB next to other apps, and meet the 5 s budget.
Measured so far (against the earlier two-field schema; the bar carries over):

| Model | Result on example 001 | Speed on the Mac |
|---|---|---|
| `qwen3:8b`, thinking off | **Fails.** Echoed the Italian instead of translating; read `IU3 F E JDE` as one call sign and "il grande Lino" as "a great line". | 20 tok/s; 14 s warm, 24 s cold |

Next candidates, available in Ollama and untested: `gemma4:12b` (the strongest multilingual line),
`qwen3.5:9b`. The choice is made in v0.2 against the golden examples.

**Cloud model.** Claude Opus 5.5 (`claude-opus-5-5`, $4 / $20 per million input / output tokens) by
default, at low effort; Claude Fable 5.1 (`claude-fable-5-1`, $10 / $50) by configuration. At an estimated
~3K input and ~1K output tokens per press: Opus ≈ $0.03, Fable ≈ $0.08. The cost is user-controlled —
one press, one call — and displayed per call and per session. Instructions and glossary form a stable
prefix for prompt caching across presses.

## Configuration and the config panel

- **The config file** (`sruti.toml`): receiver `host:port`, frequency, `cw_pboff` and the decoder
  parameters (training, threshold mode and value, word-space correction), the client identity (`sruti`),
  the output languages (`language.local`, `language.cloud`), the segmenter thresholds, the model names and
  budgets. **`.env` holds only the Claude API
  key** (`ANTHROPIC_API_KEY`); no key ever lives in `sruti.toml` or in code.
- **The config panel** (a TUI screen in v1, a page in v2) edits the connection settings and shows the
  **capture inspector**: the live raw extension messages exactly as they arrive from the receiver's API
  (`cw_chars`, `cw_wpm`, `cw_train`, and anything unrecognized), next to how sruti parsed each one — so it
  is verifiable what has to be captured from the API and how, before and while listening. Changes are
  saved to the config file and applied on reconnect.

## Hosts

- **The Mac** (M1 Pro, 32 GB, managed): runs everything; Ollama is installed. Constraints: no SDR
  software, inbound connections destroyed by endpoint filtering — which is why the v2 web interface binds
  to `127.0.0.1` only — outbound HTTPS and WebSocket work.
- **`ich-picobox`** (Ubuntu 22.04, x86-64, 4 cores, 15 GB, no GPU, on the LAN): not used in v1. A possible
  later home for the receiver link or own SDR hardware; too weak for the local model.

## Testing

- **Unit** — segmenter rules, `cw_chars` decoding, glossary rendering, prompt assembly, output-schema
  validation, session-store round-trip and replay, the interface's view models (pure presentation logic).
- **Fake receiver** — replays recorded extension messages from session files, so the whole pipeline runs
  without a network.
- **TUI, headless** — the Textual app is driven by its test pilot over the fake receiver; no terminal
  needed in CI.
- **Models are mocked by default.** No test calls Ollama or the Claude API unless asked to.
- **Golden-example eval** (opt-in) — runs a real model over `specification/examples/`, records quality
  notes and latency; the basis of every model and prompt choice.
- **Live check** (opt-in) — the NCDXF/IARU beacons on 14.100 MHz send known call signs at 22 WPM on a
  3-minute cycle: a real signal with a known answer.
