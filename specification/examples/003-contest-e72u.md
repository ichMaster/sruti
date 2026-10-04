# Example 003 — contest run, E72U

**Source:** Trémolat KiwiSDR (`sdr.autreradioautreculture.com:8073`), 7027.50 kHz, 2026-10-04 05:45 UTC,
238 s; recording `recordings/conversation.{wav,jsonl}`. Text from sruti's prototype decoder after the
v0.1 review (the baseline in `recordings/README.md`). E72U, Bosnia and Herzegovina, "runs" during the TRC
DX Contest. It holds a frequency and works one caller after another: the caller sends its call sign, E72U
answers `<call> 5NN <serial>`, the caller replies `TU 5NN <its serial> TRC`, and E72U closes with
`TU E72U` or calls `TEST E72U` when nobody answers. E72U's serials run 056 to 064 in cut numbers (`T` =
0). E72U is strong; the callers are weaker and decode worse.

## Pieces

Cut by ARCHITECTURE §Pieces and sessions. Contest exchanges use no end-of-turn prosign. Pieces 1–3 end on
≥ 3 s pauses found in the envelope (at 16.5, 28.1 and 41.2 s); after that the callers follow without a gap,
so pieces 4–5 end at the 200-character cap, splitting `5NN | T59`. Piece 6 ends with the recording.

```text
IUU E72U EETE I[err] T F6FTI 5NN T56 INA I E [err]E
```
```text
TD I E EI EB NR E E[err]
```
```text
IE IE I F CALL? T EEEIE
```
```text
EE E E TU E72U SP1AE N SP1AE N DP1AEN 5NN T57 TU 5NN6 16 TRC TU[err]2U YL2TD YL2TD 5NN T58 ? E YL2TD 5NN T58 TU 5NN 485 TRC TU E72U I TEST E72U E72U TEST E72U E72U [err]Z3ZZ E I ZZ E LZ3ZZ LZ3ZZ 5NN
```
```text
T59 5NN 391 TRC TU NMQSMGNF YO3GNF 5NN T60 A 5NN 1TU ETU E72U SOQU SP3VT E E SP3VT 5NN T61 TU 5NN 4T6 T TU O[err]KU R UOM3CNF 5NN T62 G M3CPF 5NNE281 E ETU EZ OM3CPF TU EE 4W3WU UW3WU 5NN T63 5NN 15T
```
```text
E E TU E72U YO4TL YO4TL 5NN T64 M
```

## Reference — piece tier

### Piece 1 · append

| Token | Meaning |
|---|---|
| `IUU` | [...] damaged, probably TU (?), thanks, closing the previous contact |
| `E72U` | call sign E72U, Bosnia and Herzegovina, the running station |
| `EETE I[err] T` | [...] unreadable, a weak caller |
| `F6FTI` | call sign F6FTI, France |
| `5NN` | 599, signal report |
| `T56` | 056, E72U's serial number (`T` = 0) |
| `INA I E [err]E` | [...] unreadable, F6FTI's reply |

**Message:** E72U, running in the contest: F6FTI, you're 599, number 056. F6FTI's reply is unreadable.

### Piece 2 · none

| Token | Meaning |
|---|---|
| `TD I E EI EB` | [...] unreadable |
| `NR` | number (?), perhaps asking for a serial again |
| `E E[err]` | [...] unreadable |

**Message:** — (unreadable; nothing certain to add)

### Piece 3 · append

| Token | Meaning |
|---|---|
| `IE IE I F` | [...] unreadable |
| `CALL?` | call? (your call sign, please) |
| `T EEEIE` | [...] unreadable |

**Message:** [...] Call sign, please? (someone asks a caller to repeat its call) [...]

### Piece 4 · append

| Token | Meaning |
|---|---|
| `EE E E` | [...] fragments |
| `TU` | thanks (closing the previous contact) |
| `E72U` | E72U |
| `SP1AE N` | SP1AEN, Poland, calling (split) |
| `SP1AE N` | (repeated) |
| `DP1AEN` | SP1AEN (?), E72U repeating the call, damaged (D/S) |
| `5NN` | 599 |
| `T57` | 057 |
| `TU` | thanks (SP1AEN replying) |
| `5NN6 16` | 599 616: SP1AEN's report and serial (run together and split) |
| `TRC` | TRC, a tag closing the callers' exchange in this contest (?) |
| `TU[err]2U` | TU E72U (damaged): thanks, E72U |
| `YL2TD` | call sign YL2TD, Latvia, calling |
| `YL2TD` | (repeated) |
| `5NN` | 599 |
| `T58` | 058 |
| `?` | a query (repeat?) |
| `E` | [...] fragment |
| `YL2TD` | YL2TD (E72U repeats) |
| `5NN` | 599 |
| `T58` | 058 (sent again) |
| `TU` | thanks |
| `5NN` | 599 |
| `485` | 485, YL2TD's serial |
| `TRC` | TRC (?) |
| `TU` | thanks |
| `E72U` | E72U |
| `I` | [...] fragment |
| `TEST` | TEST: a contest CQ, calling any station |
| `E72U` | E72U |
| `E72U` | (repeated) |
| `TEST` | TEST, contest CQ |
| `E72U` | E72U |
| `E72U` | (repeated) |
| `[err]Z3ZZ E I ZZ E` | [...] damaged copies of the next caller's call sign (?) |
| `LZ3ZZ` | call sign LZ3ZZ, Bulgaria, calling |
| `LZ3ZZ` | (repeated) |
| `5NN` | 599 (the serial follows in the next piece) |

**Message:** Thanks, E72U. SP1AEN calls; E72U: SP1AEN 599 057; SP1AEN: thanks, 599 616 TRC. YL2TD calls;
E72U: YL2TD 599 058, sent again after a query; YL2TD: thanks, 599 485 TRC. E72U thanks him and calls TEST
(a contest CQ) twice. LZ3ZZ calls; E72U: LZ3ZZ 599 …

### Piece 5 · append

| Token | Meaning |
|---|---|
| `T59` | 059, the serial for LZ3ZZ (its 599 ended the previous piece) |
| `5NN` | 599 |
| `391` | 391, LZ3ZZ's serial |
| `TRC` | TRC (?) |
| `TU` | thanks |
| `NMQSMGNF` | [...] a damaged copy of the next call sign, probably YO3GNF (?) |
| `YO3GNF` | call sign YO3GNF, Romania |
| `5NN` | 599 |
| `T60` | 060 |
| `A` | [...] fragment |
| `5NN` | 599 |
| `1TU` | 1… and TU (?): the start of YO3GNF's serial run into "thanks" |
| `ETU` | TU, thanks (with a stray E) |
| `E72U` | E72U |
| `SOQU` | [...] unreadable |
| `SP3VT` | call sign SP3VT, Poland |
| `E E` | [...] fragments |
| `SP3VT` | SP3VT (E72U repeats) |
| `5NN` | 599 |
| `T61` | 061 |
| `TU` | thanks |
| `5NN` | 599 |
| `4T6` | 406, SP3VT's serial (`T` = 0) |
| `T` | [...] fragment |
| `TU` | thanks |
| `O[err]KU R UOM3CNF` | [...] damaged; probably the next caller, OM3CPF (?) |
| `5NN` | 599 |
| `T62` | 062 |
| `G M3CPF` | [...] OM3CPF (?), the first letter lost |
| `5NNE281` | 599 281 (?): OM3CPF's report and serial, run together with a stray E |
| `E ETU` | TU, thanks (with stray letters) |
| `EZ` | [...] fragment |
| `OM3CPF` | call sign OM3CPF, Slovakia |
| `TU` | thanks |
| `EE` | [...] fragment |
| `4W3WU` | a damaged copy of the next call sign: the repeat shows UW3WU (?) — not a 4W (Timor-Leste) station |
| `UW3WU` | call sign UW3WU, Ukraine |
| `5NN` | 599 |
| `T63` | 063 |
| `5NN` | 599 |
| `15T` | 150, UW3WU's serial (`T` = 0) |

**Message:** LZ3ZZ, 059; LZ3ZZ: 599 391 TRC. YO3GNF: 599 060; YO3GNF: 599 1… (rest lost), thanks. SP3VT:
599 061; SP3VT: 599 406. OM3CPF (?): 599 062; OM3CPF: 599 281 (?); thanks, OM3CPF. UW3WU: 599 063;
UW3WU: 599 150.

### Piece 6 · append

| Token | Meaning |
|---|---|
| `E E` | [...] fragments |
| `TU` | thanks |
| `E72U` | E72U |
| `YO4TL` | call sign YO4TL, Romania, calling |
| `YO4TL` | (repeated) |
| `5NN` | 599 |
| `T64` | 064 |
| `M` | [...] fragment; the recording ends |

**Message:** Thanks, E72U. YO4TL calls; E72U: YO4TL 599 064. (The recording ends.)

## Reference — session tier

The bar for **section 4**, drafted by Claude Opus 5.5 with `poc/explain_session.py` (2026-10-04, effort low) and lightly edited.

> Вітаю, ви впіймали **контест**, тобто радіоаматорські змагання. Головна станція тут **E72U** з Боснії і Герцеговини. Вона сидить на одній частоті й кличе «TEST», а інші станції по черзі відгукуються. Кожен зв'язок займає кілька секунд: позивний, рапорт, порядковий номер, «дякую» і одразу наступний. Декодер місцями плутає літери (наприклад, «IUU», «NMQSMGNF», «SOQU»). Початок сесії (шматки 1–3) здебільшого нерозбірливий.
>
> Приблизний переклад, з прибраними повторами:
>
> «...F6FTI, 599, ваш номер 056...» (далі нерозбірливо)
>
> «...позивний?..» (схоже на перепитування позивного, але це лише здогад за уривком «CALL?»)
>
> «Дякую, це E72U. SP1AEN, 599, номер 057.» Відповідь: «Дякую, 599, 616.»
>
> «YL2TD, 599, номер 058.» Відповідь: «599, 485.»
>
> «E72U, змагання.» (кілька разів)
>
> «LZ3ZZ, 599, номер 059.» Відповідь: «599, 391.»
>
> «YO3GNF, 599, номер 060.»
>
> «SP3VT, 599, номер 061.» Відповідь: «599, 406.»
>
> «OM3CPF, 599, номер 062.» Відповідь: «599, 281.»
>
> «UW3WU, 599, номер 063.» Відповідь: «599, 150.»
>
> «Дякую, E72U. YO4TL, 599, номер 064...»
>
> **Позивні.**
> - **E72U** — Боснія і Герцеговина.
> - **F6FTI** — Франція.
> - **SP1AEN** і **SP3VT** — Польща. В одному місці декодер дав «DP1AEN». Скоріше за все, це та сама станція SP1AEN, просто з помилкою в першій літері, але напевно сказати не можна.
> - **YL2TD** — Латвія. Тут YL стоїть на місці позивного, тож це префікс країни, а не «young lady».
> - **LZ3ZZ** — Болгарія.
> - **YO3GNF** і **YO4TL** — Румунія.
> - **OM3CPF** — Словаччина. Перед ним промайнуло спотворене «UOM3CNF», це, ймовірно, перша невдала спроба розібрати той самий позивний.
> - **UW3WU** — Україна. Йому передувало «4W3WU», найпевніше та сама станція з помилкою декодера.
>
> **Скорочення й числа.**
> - **5NN** — це «599», найкращий рапорт якості сигналу. N тут замінює цифру 9.
> - **T** замість нуля: T56 означає 056, 4T6 означає 406, 15T означає 150.
> - Числа після рапорту — порядкові номери зв'язків у змаганні.
> - **TU** — «дякую», **TEST** — заклик учасникам контесту.
> - **TRC** закриває обмін більшості кореспондентів. З тексту не ясно, чи це частина контрольного обміну змагання, чи клубна позначка.
>
> Загалом це швидкий, майже конвеєрний контест-ран: жодних розмов, лише позивний, рапорт, номер і наступна станція.

## What the decoder got wrong

| Decoded | Intended | Note |
|---|---|---|
| `SP1AE N`, `DP1AEN` | `SP1AEN` | a spurious space; D/S confused |
| `5NN6 16`, `5NNE281` | `5NN 616`, `5NN 281` | run together, split, a stray letter |
| `TU[err]2U` | `TU E72U` | |
| `NMQSMGNF` | `YO3GNF` (?) | first sending damaged |
| `O[err]KU R UOM3CNF`, `G M3CPF` | `OM3CPF` (?) | damaged before the clean `OM3CPF` |
| `4W3WU` | `UW3WU` | `4` and `U` differ by one element; `4W` is a real prefix, so the repeat decides |
| pieces 1–3 | — | weak callers: mostly unreadable, must be marked, not guessed |

## Ambiguity a good answer keeps open

- Damaged first copies of a call sign (`NMQSMGNF`, `4W3WU`) are read through the clean repeat, and an
  answer says so; it never reports them as other stations.
- `TRC` closes most callers' exchanges; whether it is part of the contest exchange or a club tag is not
  certain from the text.
- Who sent `NR` and `CALL?` in pieces 2–3 is not certain.

## The bar for a passing answer

- Recognises a contest run: one strong station (E72U) working many callers fast, `TEST` as the contest
  CQ, `TU` closing each contact.
- Reads the cut numbers (`T56` = 056, `4T6` = 406, `15T` = 150) and `5NN` = 599, and that each exchange
  is a report plus a serial number.
- Copies every call sign exactly: E72U, F6FTI, SP1AEN, YL2TD, LZ3ZZ, YO3GNF, SP3VT, OM3CPF, UW3WU, YO4TL,
  with countries.
- Does not repeat `TEST E72U E72U` or the doubled calls in the message.
- Marks the unreadable callers' text instead of inventing it.
