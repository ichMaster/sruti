# Mission — sruti

## In one sentence

sruti is a listening agent: it tunes into a public WebSDR receiver, reads the Morse code (CW) it hears as
text, and explains in real time what is being said — word by word, as a readable message, and, on demand,
as the full picture in Ukrainian.

## What we are building

Amateur-radio CW is dense. It is made of abbreviations, Q-codes, prosigns and call signs, in whatever
language the operators share, and the decoders that turn it into text drop, split and merge letters. sruti
turns that into three levels of meaning, shown side by side with the original:

1. **Word by word (gloss)** — each token of the decoded text mapped to its meaning in English:
   `HW?` → "how (do you copy)?", `K` → "over", `IZ4PHG` → "Italian call sign, Emilia-Romagna".
2. **The message** — the text restored and translated into natural English: `HW? K` → "how do you copy?
   over".
3. **What is going on (explanation)** — the whole conversation explained **in Ukrainian**: who is talking
   to whom, and what kind of exchange it is — a CQ call, a report exchange, a friendly conversation, a
   beacon.

Two language models share the work. A **local model** on the Mac produces the gloss and the message for
each piece within seconds — in near real time, buffered by piece, never word by word — for free and
without a network. A **cloud model** (Claude Opus 5.5, or Fable 5.1 by configuration) produces the
Ukrainian explanation **only when the user asks for it**, at the push of a button, over the whole session.
The quality bar is the reference answer in [examples/001-italian-ragchew.md](examples/001-italian-ragchew.md).

**The interface is a terminal app (TUI) in v1**, with four sections — original text, word by word,
message, what is going on — plus a config panel for the receiver connection and a session switcher. **v2
puts the same four sections in the browser**, served only on localhost; the core is UI-agnostic and does
not change.

**Everything heard is kept.** A session is one stretch of listening on one receiver and frequency; it is
switched manually — switching the session *is* retuning — and every session is saved and can be reopened
and replayed.

The receiver is someone else's: a public **KiwiSDR** reached over the internet. The text comes first from
the receiver's own CW decoder; decoding the audio on the Mac is a later version.

## For whom

A private tool for its author, running on a managed work Mac (M1 Pro, 32 GB) where SDR software cannot be
installed and nothing can accept an inbound connection. One user, one terminal, listening only.

## Principles

- **Listen only.** sruti never transmits and has no path to a transmitter.
- **Outbound only.** Every connection is opened from the Mac outward: the receiver WebSocket, Ollama on
  localhost, the Claude API. The Mac's endpoint filtering destroys inbound LAN connections, so the design
  never needs one — the v2 web interface binds to localhost only.
- **No radio software, no hardware.** SDR software is blocked on this Mac and no SDR is attached; the
  radio is a public KiwiSDR.
- **Decode at the receiver first.** The KiwiSDR's own CW decoder produces the text. Decoding on the Mac is
  a later version.
- **Two tiers of language model.** Local for latency, cost and privacy, buffered by piece; cloud for
  quality, **only on the user's push**. The agent is fully usable with the cloud tier off.
- **The interface is a shell.** The core — receiver, segmenter, store, explainers — is UI-agnostic; the
  TUI (v1) and the web page (v2) render the same events and send the same commands.
- **Every session is kept.** Sessions are switched manually (switching = retuning), always saved, and
  replayable.
- **Never invent.** Unreadable text is marked `[...]`, not guessed. A call sign is never "corrected" into
  a different call sign. Uncertainty is said out loud.
- **The glossary is data.** Q-codes, prosigns and abbreviations live in a versioned file given to the
  models, not in model memory.
- **Measured, not felt.** Model and prompt choices are judged against golden examples — recorded decoder
  output with a reference explanation.
- **A polite guest.** Public receivers have few slots: one connection, a clear user name, respect for the
  receiver's time limits, disconnect when idle.

## Non-goals

- Transmitting, keying, or anything that talks back on the air.
- SDR software or SDR hardware on the Mac; websdr.org receivers (browser-only, no programmatic interface).
- Digital modes (FT8, RTTY, PSK) and voice (SSB) transcription.
- Contact logging, QSL, contesting.
- A browser UI in v1 — v1 is the TUI; the web interface is v2, and it never faces the LAN or the internet.

## Glossary

- **CW** — Morse code telegraphy ("continuous wave").
- **WebSDR / KiwiSDR** — a radio receiver shared over the web. sruti uses KiwiSDR: about 870 public
  receivers, an open WebSocket protocol and a Python client. websdr.org receivers are browser-only.
- **Receiver link** — sruti's connection to one KiwiSDR: an audio channel plus the receiver's CW decoder
  extension.
- **Piece** — a run of decoded text cut at a pause or an end-of-turn prosign; the unit the local model
  explains. The local tier's buffer.
- **Session** — the pieces heard on one receiver and one frequency between tune and retune. Switched
  manually (switching = retuning), always saved, replayable.
- **QSO** — a radio contact between stations.
- **Prosign** — a procedural signal: `K` (over), `KN` (over, only you), `BK` (back to you), `AR` (end of
  message), `SK` (end of contact).
- **Gloss / Message / Explanation** — the three outputs: the word-by-word mapping (English), the readable
  translation (English), and the on-demand full picture (Ukrainian) — sections 2, 3 and 4 of the
  interface.
- **Local tier** — the Ollama model on the Mac, called per piece; it produces the gloss and the message.
- **Cloud tier** — the Claude model, called over the whole session only when the user presses Explain; it
  produces the explanation.
- **Golden example** — recorded decoder text with a reference explanation, used to evaluate models and
  prompts.
