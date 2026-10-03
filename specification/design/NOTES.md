# sruti window — design notes

Deliverable for [BRIEF.md](BRIEF.md) §7.

- `index.html` — the window as one self-contained file. Opened in Safari or Chrome with no app attached, it plays example 001 by itself (demo mode).
- `screenshots/` — 1320×860 PNGs: live listening, Explain result, read-only view, Sessions panel, Config + capture inspector, live in dark mode.
- Source: `Sruti Window.dc.html` in the design project (the editable version `index.html` is compiled from).

## Layout

A header bar over a 2×2 grid of the four sections — **1 Original text** and **2 Word by word** on top, **3 Message** and **4 What is going on** below — so every section gets a full half-width line. Sessions and Config slide in from the right over a scrim; New session is a popover under its button. A demo bar at the bottom exists only in demo mode.

Visual system: steel-blue accent on a light technical ground, Barlow Condensed headings, Barlow body, `ui-monospace` for decoded text, tokens and raw messages. Sections are flat panels with a hairline border and a 4px radius; Explain, Tune and Save are the only solid (primary) buttons.

## Components

- **Header** — wordmark śruti; session name (click to rename in place: Enter saves, Esc or click-away cancels; long names ellipsize); receiver · kHz · start time; link-status chip; running costs (Gemini · 2–3, Opus · 4); Stop / Start listening; New session; Sessions; Config.
- **1 Original text** — the stream in monospace; `[err]` as a dashed, tinted mark; a dashed divider after each piece ("piece 2 · closed on pause"); a blinking caret at the live end.
- **2 Word by word** — one block per piece: header (piece number · latency · cost), then the piece written out **as running text, like section 1, with each token's meaning right after it** in a small tinted label (`CAMBIO change ANCHE also …`). A token and its meaning never break apart; tokens keep their inner spaces (`SOT T O`); `(?)` stays verbatim.
- **3 Message** — one entry per piece: the sentence and "piece N". **×n** tag when following pieces only repeated it; a **⟲ rewritten · pieces 2–3** block drawn as a dashed frame around the replaced entries; corrections begin with an accent "correction:".
- **4 What is going on** — Explain button in the header; Ukrainian paragraphs in the system face (Barlow has no Cyrillic), «quoted translations» indented in accent ink, a footer line (model · up to piece N · seconds · cost).
- **Piece linking** — hovering a piece in 1, 2 or 3 tints the same piece in the other two.
- **Auto-scroll** — 1–3 (and the inspector) follow the newest content; scrolling up pauses it and shows a **↓ Newest** button in that section's header.
- **Capture inspector** — under the Config form: time, direction (→ sent, ← received), raw message in monospace, parsed meaning; last 400 rows, auto-scrolls.

## States

Every state in BRIEF §4 opens from the demo bar's **State** menu or a URL hash, e.g. `index.html#state=explaining`. The demo bar also switches System / Light / Dark.

| Group | Hash ids |
|---|---|
| Window | `live` (plays from the start), `full`, `readonly`, `new`, `sessions`, `config` |
| Link status | `connecting`, `lull`, `busy`, `time_limit`, `reconnecting`, `stopped`, `ended` |
| Sections 2–3 | `waiting`, `no_expl`, `no_gemini` |
| Section 3 entries | `repeat`, `rewritten`, `correction` |
| Section 4 | `s4_empty`, `explaining`, `result`, `failed`, `claude_off`, `s4_readonly` |
| Edge content | `long_name`, `long_token`, `two_hour` |

- **Link-status dot** (one accent only, so states differ by shape and words): listening = pulsing solid dot; lull = dimmed dot; connecting / reconnecting = pulsing ring; receiver busy / time limit = solid square; stopped / recording ended = grey ring. Busy counts down "retry in N s".
- **Section 4**: empty = invitation + price; explaining = button disabled, progress line with elapsed seconds and a thin scanning bar, the previous answer dimmed below; failed = dashed note on top, previous answer kept; off = "no Claude key" hint; read-only = Explain disabled, the saved explanation (if any) shown with a note.
- **Sections 2–3**: waiting hint; "No explanation — raw text only" for a piece whose call failed; one-line `GEMINI_API_KEY` hint when the key is missing.
- **Read-only** — banner "Viewing a saved session: <name> · read-only" with **Back to live**; status shows "Recording ended"; Stop/Start disabled. The live session keeps receiving events in the background.
- **Dark** — follows `prefers-color-scheme`; the tonal ramps are mirrored so every token keeps its role.

## Wiring

Exactly BRIEF §8: the page defines `window.sruti.onEvent(event)` and, after `pywebviewready`, calls `window.pywebview.api.ready()`, `tune`, `start`, `stop`, `explain`, `list_sessions`, `open_session`, `rename_session`, `get_config`, `set_config`. Event text is rendered as text nodes, never parsed as HTML. No `alert` / `confirm` / `prompt`. Esc closes panels and the form; Enter submits; focus ring is the 2px accent outline; motion stops under `prefers-reduced-motion`.

## Changes from the brief and open points

- **Fonts.** §6 asks for system fonts only. The design uses Barlow / Barlow Condensed; they are **embedded inside `index.html`**, so the file makes no network requests. If you want strict system fonts, swap `--font-heading` / `--font-body` to `-apple-system` — layout survives it.
- **Build.** `index.html` is a compiled bundle (≈400 KB, includes a small rendering runtime) rather than hand-written plain JS. It is still one self-contained file with no CDN or build step on your side; edit the source and recompile to change it.
- **Content I wrote** beyond §5, to show states: the full gloss of piece 2 and the gloss of piece 3 (from example 001's error table), the ×3 repeat piece `R R IZ4PHG DE IU2PEJ K`, the rewritten block for pieces 2–3, the correction text, and two saved sessions ("Italian ragchew", 2026-10-01 22:05).
- **Explain** is disabled until at least one piece has closed.
- A rebuild (`action: "rebuild"` with *k* strings) replaces the last *k−1* entries plus the current piece and marks them as one rewritten block.
