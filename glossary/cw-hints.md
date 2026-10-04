# CW hints

A short list of what models get wrong on decoded CW. Standard Q-codes, prosigns and abbreviations
are not listed: use your own knowledge for those, and for the operators' language.

## How the decoder damages text

- Spurious spaces split words: `RIP ASS O` = RIPASSO, `SOT T O` = SOTTO.
- Missing spaces run words together, often a call sign with `DE`: `JDE` may be `J DE`.
- A letter is lost, most often the first one: `ORSE` = FORSE.
- Letters one Morse element apart get swapped: S/U/V, F/H, D/B, A/N/R, I/S/H, E/T, M/O.
- Accented letters have no standard Morse code and come out as `[err]` (Italian È, À; German Ä, Ö, Ü).
- Reconstruct a word when context makes it clear, and say it is a reconstruction. If the text is
  unreadable, write `[...]` and do not guess.

## Habits that are easy to misread

- Italian `ET` means "e" (and). Operators send ET because a lone E (one dot) is easily lost.
- Italian `CAMBIO` means "over", I hand the turn back. `TI RIPASSO IL CAMBIO` = "back to you".
- Cut numbers appear only in numbers, reports and contest serials: T = 0, N = 9, A = 1 (`5NN` = 599,
  `5TT` = 500, `T56` = 056, `4T6` = 406). A T or E inside ordinary text is a letter, not a digit.
- Read a report as sent: `5 5N` with a spurious space is 559, not 599. Only `5NN` is 599.
- A lone letter between exchanges (`E`, `I`, `T`, `A`) is a fragment of noise or of a weaker station:
  gloss it as a fragment, not as a word or a digit.
- `ES`, `OM` and `YL` are prefixes only where a call sign stands. In running text they mean
  "and", "old man" and "young lady".

## Contests and park activations

- `TEST` is a contest call. A running station works callers fast: it sends `<call> 5NN <serial>`, the
  caller replies `TU 5NN <its serial>`, and `TU <call>` or `TEST <call>` opens the next contact. The
  repeats carry no new content.
- `CQ POTA` is a park activation (Parks on the Air); `/P` after a call sign means portable.
- `AGN` = again; `NR?` = your serial number?; `CALL?` = your call sign?

## Call signs

- A call sign is a prefix (country), a digit (often a region) and a suffix: `IZ4PHG`, `DL1ABC`, `OH2B`.
- Copy a call sign exactly as sent. Never change it into another call sign.
- If you join split fragments into a call sign (`IU3 F E J` → IU3FEJ), mark it `(?)`.
- Two call signs that differ by one Morse element may be one station decoded twice. Say so; do not
  merge them silently.
- A damaged first copy of a call sign is usually read through a clean repeat nearby. Never offer a
  call sign that does not appear in the text, not even as an alternative with a question mark.
