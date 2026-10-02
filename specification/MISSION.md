# Mission — sruti

## In one sentence

sruti is a listening agent: it tunes into a public WebSDR receiver, reads the Morse code (CW) it hears as text, and explains in Ukrainian, in real time, what is being said and what is going on.

## What we are building

Amateur-radio CW is dense. It is made of abbreviations, Q-codes, prosigns and call signs, in whatever language the operators share, and the decoders that turn it into text drop, split and merge letters. sruti turns that into two levels of meaning:

1. **Plain language (L1)** — the text restored and translated into Ukrainian, abbreviations expanded: `HW? K` → «як чуєш? прийом».
2. **What it is about (L2)** — one to three sentences: who is talking to whom, and what kind of exchange it is — a CQ call, a report exchange, a friendly conversation, a beacon.

Two language models share the work. A **local model** on the Mac explains each piece of transmission within seconds, for free and without a network. A **cloud model** (Claude Opus 5.5 or Fable 5.1) runs every few minutes over the whole conversation and produces the polished version. The quality bar is the reference answer in [examples/001-italian-ragchew.md](examples/001-italian-ragchew.md).

The receiver is someone else's: a public **KiwiSDR** reached over the internet. The text comes first from the receiver's own CW decoder; decoding the audio on the Mac is a later fallback.

## For whom

A private tool for its author, running on a managed work Mac (M1 Pro, 32 GB) where SDR software cannot be installed and nothing can accept an inbound connection. One user, one terminal, listening only.

## Principles

- **Listen only.** sruti never transmits and has no path to a transmitter.
- **Outbound only.** Every connection is opened from the Mac outward: the receiver WebSocket, Ollama on localhost, the Claude API. The Mac's endpoint filtering destroys inbound LAN connections, so the design never needs one.
- **No radio software, no hardware.** SDR software is blocked on this Mac and no SDR is attached; the radio is a public KiwiSDR.
- **Decode at the receiver first.** The KiwiSDR's own CW decoder produces the text. Decoding on the Mac is v2.
- **Two tiers of language model.** Local for latency, cost and privacy; cloud for quality, on a timer and only when there is new text. The agent is fully usable with the cloud tier off.
- **Never invent.** Unreadable text is marked `[...]`, not guessed. A call sign is never "corrected" into a different call sign. Uncertainty is said out loud.
- **The glossary is data.** Q-codes, prosigns and abbreviations live in a versioned file given to the models, not in model memory.
- **Measured, not felt.** Model and prompt choices are judged against golden examples — recorded decoder output with a reference explanation.
- **A polite guest.** Public receivers have few slots: one connection, a clear user name, respect for the receiver's time limits, disconnect when idle.

## Non-goals

- Transmitting, keying, or anything that talks back on the air.
- SDR software or SDR hardware on the Mac; websdr.org receivers (browser-only, no programmatic interface).
- Digital modes (FT8, RTTY, PSK) and voice (SSB) transcription.
- Contact logging, QSL, contesting.
- A GUI in v1 — the terminal is the interface.

## Glossary

- **CW** — Morse code telegraphy ("continuous wave").
- **WebSDR / KiwiSDR** — a radio receiver shared over the web. sruti uses KiwiSDR: about 870 public receivers, an open WebSocket protocol and a Python client. websdr.org receivers are browser-only.
- **Receiver link** — sruti's connection to one KiwiSDR: an audio channel plus the receiver's CW decoder extension.
- **Piece** — a run of decoded text cut at a pause or an end-of-turn prosign; the unit the local model explains.
- **Session** — the pieces of one conversation on one frequency; the context both models see. Ends on `SK`, a frequency change or a long silence.
- **QSO** — a radio contact between stations.
- **Prosign** — a procedural signal: `K` (over), `KN` (over, only you), `BK` (back to you), `AR` (end of message), `SK` (end of contact).
- **L1 / L2** — the two levels of explanation: plain language / what it is about.
- **Local tier** — the Ollama model on the Mac, called per piece.
- **Cloud tier** — the Claude model, called periodically over the whole session.
- **Golden example** — recorded decoder text with a reference explanation, used to evaluate models and prompts.
