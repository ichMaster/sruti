# Design brief — the sruti window

**For:** Claude Design. **Goal:** the visual design of sruti's one window, delivered as a working HTML
page that the app can load as-is (§7). The functions and their rules below are fixed by the project
specification; the look is yours.

## 1. The product

sruti is a private listening tool for one person on a Mac. It connects to a public web radio receiver
(a KiwiSDR), takes its audio, decodes the Morse code (CW) of amateur radio conversations into text with
its own decoder, and explains what it hears. The decoded text is damaged — letters dropped, words split,
`[err]` for unknown codes — and dense with abbreviations, so the window shows it at four levels side by
side, live:

1. **Original text** — exactly what sruti's decoder produced, character by character.
2. **Word by word** — each token of a piece and what it means (English).
3. **Message** — what the operator actually said, as a natural English sentence.
4. **What is going on** — the whole conversation explained in Ukrainian, only when the user asks.

The user listens for long stretches, often an hour, reads while text streams in, and occasionally
presses **Explain**. The tone to aim for: a calm listening console — readable for hours, dense without
clutter, the raw signal always visible.

## 2. Vocabulary

- **Piece** — a run of decoded text that ends when the operator hands over or pauses. It is the unit that
  gets explained: sections 2 and 3 update once per piece, never per character.
- **Session** — everything heard on one receiver and one frequency. A new session starts only when the
  user retunes. Every session is saved, can be renamed and reopened read-only.
- **Prosign / Q-code / call sign** — CW conventions: `K` (over), `QSO` (a contact), `IZ4PHG` (a station).

## 3. The window

One desktop window, default 1320×860, minimum 980×640. No mobile layout.

### 3.1 Header

- Wordmark **śruti**.
- **Session name**, click to rename in place (Enter saves, Esc cancels). Auto-names look like
  `2026-10-02 21:40 · <receiver> · 7020 kHz`; user names look like "Italian ragchew".
- Receiver (`host:port`), frequency (kHz), session start time.
- **Link status** with the decoder's reading, e.g. "listening · 22 WPM · tone 620 Hz · 21 dB" — speed,
  the tone it locked on, signal over noise (all states in §4).
- **Stop / Start listening** toggle.
- **Running costs**: Gemini (sections 2–3, grows by about $0.003 per piece) and Opus (section 4, about
  $0.03 per Explain).
- Buttons: **New session**, **Sessions**, **Config**.

### 3.2 The four sections

All four are visible at once (the prototype uses a 2×2 grid; propose better if you have it) and keep
their numbers 1–4 and names — the user and the specification refer to them that way.

| # | Name | Content | Updates |
|---|---|---|---|
| 1 | Original text | decoded characters in a monospace face; `[err]` marked; a divider after each piece ("piece 2 · closed on pause") | live, every character (5–10 per second, for hours) |
| 2 | Word by word | one block per piece: header (piece number, model latency, cost) and token → meaning rows; tokens can contain spaces (`SOT T O`); uncertain readings carry `(?)` | when a piece closes |
| 3 | Message | one entry per piece: the sentence and its piece number; a **×n** counter when a piece only repeated the last one; a **⟲ rewritten** mark when recent entries were replaced; corrections read "correction: …" | together with section 2; entries are never edited, only appended, counted or rewritten as a marked block |
| 4 | What is going on | the **Explain** button and the explanation: Ukrainian paragraphs, quoted translations in «guillemets», then a footer line (model, "up to piece N", seconds, cost) | only when the user presses Explain; the new answer replaces the old one |

Sections 1–3 auto-scroll to the newest content unless the user has scrolled up to read.

### 3.3 New session

A small form under **New session**: frequency in kHz (required, 100–30000) and receiver `host:port`
(optional, defaults to the current one). Inline validation message. Submitting starts a new session and
clears the four sections.

### 3.4 Sessions panel

A side panel listing every saved session, newest first: name, receiver, frequency, start time, number of
pieces; the current one marked **live**. Per row: **Open** (replay read-only) or **Show** for the live
one, and **Rename**. Opening a past session shows it in the same four sections with a banner: "Viewing a
saved session: <name> · read-only" and **Back to live**. Explain is disabled there.

### 3.5 Config panel and capture inspector

A side panel with the receiver connection settings and **Save** ("Saved. Applied on the next tune."):

- receiver `host:port`; frequency, kHz;
- decoder: tone (automatic, or fixed in Hz); speed (automatic, or fixed in WPM); threshold contrast, dB;
- piece pause, s; piece maximum, characters;
- language of sections 2–3; language of section 4.

Below it, the **capture inspector**: a live table of the raw messages crossing the receiver connection —
time, direction (→ sent, ← received, · the decoder), the raw message in monospace, and how sruti parsed
it. Audio frames are not listed one by one; a row every few seconds gives their signal level. Keeps the
last 400 rows and auto-scrolls. Its purpose is trust: the user checks here exactly what the receiver
sends and what the decoder makes of it.

## 4. States to design

| Area | States |
|---|---|
| Link status | connecting · listening (with WPM, tone, signal over noise) · no signal (audio arrives, the decoder hears no CW) · lull (a piece is closing) · receiver busy (retrying in N s) · receiver time limit reached · reconnecting (attempt N) · stopped by the user · recording ended (replays only) |
| Sections 2–3 | waiting for the first piece · filled · one piece without an explanation ("no explanation — raw text only") · Gemini key missing (sections 2–3 stay empty, with a one-line hint) |
| Section 4 | empty (invitation to press Explain) · explaining (button disabled, a progress line) · result · failed (previous explanation kept, plus an error note) · off — no Claude key · disabled in a read-only session |
| Section 3 entries | a normal entry · ×3 repeat · ⟲ rewritten block · a correction |
| Whole window | live session · read-only saved session · New session form open · Sessions panel open · Config panel open · light and dark appearance |
| Edge content | a 60-character session name · a long token · a two-hour session (hundreds of pieces) · Cyrillic text in section 4 |

## 5. Real content

Design with this material from a real recording (an Italian conversation); no placeholder text.

**Section 1 — three pieces, as decoded:**

```
T E TTEAEANDE CAMBIO ANCHE IL RTX ET ACCENDO L' IC 7300
ALESORA TI RIP ASS O IL CAMB IO IU3 F E JDE IZ4PHG HW K R QSO DE IU2PEJ GRAZIE PER LE INFTA EIO ORSE NON UAI CFE NON [err]T ANTO CH
E FACCIO CW MA IL MIO MAESTRO [err]L INO CIRCA 7 ANNI HO COMOS[err]IUNO IL GRANDE LINO ET LUI MI HA PRESO SOT T O LA SUA AAEA ET PE R
```

**Section 2 — piece 1 (2.1 s, $0.0018):** `T E TTEAEANDE` → [damaged text] · `CAMBIO` → change ·
`ANCHE` → also · `IL` → the · `RTX` → transceiver · `ET` → and · `ACCENDO` → turn on · `L'` → the ·
`IC 7300` → IC-7300 (radio).
Piece 2 excerpt (3.5 s, $0.0033): `ALESORA` → allora (now/then, reconstructed) · `RIP` → ripasso (split:
pass back) · `JDE` → J (IU3FEJ (?)) de (from) · `HW` → how copy? · `K` → over · `R` → roger ·
`UAI` → sai (you know, U/S error (?)) · `[err]T` → è (is).

**Section 3:**

1. [...] I am also changing transceiver and turning on the IC-7300 — *piece 1*
2. Now I pass the turn back to you, IU3FEJ (?) from IZ4PHG, how copy? Over. Roger QSO from IU2PEJ, thanks
   for the info. Maybe you don't know that it hasn't been long that [...] — *piece 2*
3. [... that] I have been doing CW, but my teacher is Lino. About 7 years ago I met the great Lino and he
   took me under his wing and for [...] — *piece 3*

**Section 4** (footer: Claude Opus 5.5 · up to piece 3 · 9.4 s · $0.03):

> Вітаю, ви впіймали живу розмову італійських радіоаматорів. Вони спілкуються звичайною італійською
> мовою, а декодер місцями помиляється з пробілами та літерами, тому текст виглядає порваним.
>
> Приблизний переклад такий:
>
> «...і ще міняю трансивер та вмикаю IC-7300.»
>
> «Тож повертаю тобі слово, IU3F..., це IZ4PHG, як приймаєш? Прийом.»
>
> «Прийняв. Це IU2PEJ, дякую за інформацію. Ти, мабуть, не знаєш, що я не так давно працюю телеграфом,
> але мій учитель Ліно... років сім тому я познайомився з великим Ліно, і він узяв мене під своє крило,
> і...»
>
> Кілька пояснень до того, що ви бачите. IZ4PHG, IU2PEJ та IU3F... це позивні операторів: літера I
> означає Італію, а цифра вказує на регіон (2 це Ломбардія, 3 це північний схід, 4 це Емілія-Романья).
> IC-7300 це популярний трансивер фірми Icom. Решта це стандартні телеграфні скорочення: DE означає «від»,
> K означає «прийом, передавай», R означає «прийняв», HW це запитання «як чуєш?», QSO це сам сеанс
> зв'язку, RTX це трансивер, а ET в італійців замінює сполучник «і».
>
> Тобто це не короткий обмін рапортами, а неспішна дружня бесіда кількох людей по колу, і один із них
> розповідає, як навчився морзянки у свого наставника.

**Capture inspector rows:**

| Time | Dir | Raw | Parsed |
|---|---|---|---|
| 21:40:02 | → | `SET auth t=kiwi p=` | log in as a public listener |
| 21:40:02 | → | `SET ident_user=sruti` | identify as sruti |
| 21:40:02 | → | `SET mod=cw low_cut=300 high_cut=700 freq=7021.980` | CW at 7021.98 kHz |
| 21:40:02 | → | `SET compression=0` | uncompressed audio |
| 21:40:03 | ← | `MSG audio_rate=12000 sample_rate=12001.135` | audio at 12 kHz |
| 21:40:03 | ← | `MSG badp=1` | all free channels taken — retrying |
| 21:40:13 | ← | `SND · 60 frames · −94 dBm` | audio arriving, signal −94 dBm |
| 21:40:15 | · | `tone 620 Hz · 22 WPM · 21 dB` | decoder locked on |

**Costs after this session:** Gemini $0.0087 · Opus $0.03.

## 6. Technical constraints

- The page runs inside a native macOS window (pywebview on the system **WebKit**, the Safari engine). It
  must work in Safari.
- **One self-contained HTML file**: inline `<style>` and `<script>`. No external fonts, CDNs, images by
  URL or anything that needs a build step. Plain JavaScript; icons as inline SVG or Unicode.
- **System fonts only**: `-apple-system` (SF Pro) for the interface, `ui-monospace` (SF Mono) for decoded
  text, tokens and raw messages; `ui-serif` (New York) is available if you want a display face. They must
  render Cyrillic (they do).
- **Light and dark** follow the system appearance (`prefers-color-scheme`); every color is a CSS custom
  property defined at the top.
- Text is selectable. Keyboard: Esc closes panels and the form, Enter submits; focus is visible; motion
  respects `prefers-reduced-motion`.
- No `alert()`, `confirm()` or `prompt()`; any confirmation lives in the page.
- Event data is always inserted as text (`textContent`), never as HTML.

## 7. Deliverable

Hand back:

1. **`index.html`** — the one self-contained file from §6, implementing the wiring in §8. Opened from disk
   in Safari or Chrome, it plays a whole session from the §5 material by itself (demo mode).
2. **A state switcher** in demo mode — a small toolbar or a URL hash such as `#state=explaining` — that
   shows every state in §4 without waiting for the demo to reach it.
3. **Design tokens** at the top of the `<style>`: colors for light and dark, type scale, spacing, radii.
4. **Screenshots**, PNG at 1320×860: live listening, the Explain result, read-only view, Sessions panel,
   Config panel with the inspector, and the live view in dark mode.
5. **Notes** — a short `NOTES.md`: the components, what each state looks like, and anything in this brief
   you changed or could not fit.

These go into `specification/design/` in the sruti repository and become the window's page in the
implementation (ROADMAP v1.5).

## 8. Wiring contract

The page talks to the app only through these two channels. Keep the names exactly; the visual structure
around them is free.

**Events in.** The page defines `window.sruti = { onEvent(event) { … } }`; the app calls it once per
event, in order.

| `type` | Fields | Meaning |
|---|---|---|
| `session` | `id, name, receiver, freq_khz, started, pieces`, `renamed?` | a new session started (clear the sections), or a rename |
| `status` | `state` (§4 link states: `connecting`, `listening`, `no_signal`, `lull`, `busy`, `time_limit`, `reconnecting`, `stopped`, `ended`), `wpm?`, `tone_hz?`, `snr_db?`, `retry_in_s?`, `attempt?` | link status and the decoder's reading |
| `raw` | `dir` (`→` / `←` / `·`), `msg`, `parsed`, `t` | one capture-inspector row |
| `char` | `ch`, `t` | one decoded unit for section 1; `[err]` arrives whole |
| `piece` | `seq, raw, cut` (`prosign` / `pause` / `length`) | a piece closed: draw its divider |
| `explanation` (`tier: "piece"`) | `piece_seq, action` (`none` / `append` / `rebuild`), `gloss` (list of `[token, meaning]`), `message?`, `rebuilt?` (list of strings), `latency_ms, cost_usd, model` — or `piece_seq, error` | sections 2–3 for one piece |
| `explanation` (`tier: "session"`) | `upto_seq, text` (paragraphs separated by blank lines), `latency_ms, cost_usd, model` | section 4 |
| `explain_state` | `state` (`running` / `idle` / `failed` / `off`), `note?` | the Explain button and progress line |
| `end` | — | the replayed recording finished |

**Commands out.** When the app is ready it fires the `pywebviewready` event; from then on the page calls
`await window.pywebview.api.<command>(…)`:

| Command | Returns |
|---|---|
| `ready()` | `{config, sessions, current, keys: {gemini, claude}}` |
| `tune(freq_khz, receiver_or_null)` | the new session |
| `start()` / `stop()` | — |
| `explain()` | `{ok}` |
| `list_sessions()` | list of sessions |
| `open_session(id)` | that session's stored events, to replay through the same rendering |
| `rename_session(id, name)` | `{ok}` |
| `get_config()` / `set_config(config)` | the config / `{ok, note}` |

**Demo mode.** When `window.pywebview` is absent — the file opened in a browser — the page feeds itself
the §5 material as events and answers its own commands, so the whole design can be reviewed without the
app.

## 9. Out of scope

A web server, routing, accounts, multiple users, phone layouts, onboarding, a spectrum or waterfall view,
and branding beyond the wordmark. The update rules in §3.2 and §4 are part of the specification, not
style: please don't change when a section updates — only how it looks.

## 10. Reference

The working prototype is `poc/desktop/index.html` in the repository: every function above, in a plain
look. Attach it and a screenshot of it as the functional baseline; restyle freely.
