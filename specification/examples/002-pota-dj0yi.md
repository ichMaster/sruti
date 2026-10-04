# Example 002 — POTA activation, DJ0YI

**Source:** Trémolat KiwiSDR (`sdr.autreradioautreculture.com:8073`), 7033.05 kHz, 2026-10-03 11:32 UTC,
177 s; recording `recordings/cq.{wav,jsonl}`. Text from sruti's prototype decoder after the v0.1 review
(the baseline in `recordings/README.md`). A German station, DJ0YI, activates a park for Parks on the Air
(POTA) and calls CQ. A Czech portable station, OK7DA/P, answers and gets a report. The answering station
is weaker, so its replies decode poorly.

## Pieces

Cut by ARCHITECTURE §Pieces and sessions: on an end-of-turn `K` standing alone, on a ≥ 3 s pause found in
the envelope (piece 4, at 143.6 s), and at the end of the recording.

```text
IEPOTA K
```
```text
CQ POTA DE DP 0YE DJ0YI POTA K
```
```text
E DEQ POTA DE DJ0YI DJ0YI POTA K
```
```text
TTK7 DA/P AGN DE O NI 7 <BT>[err] OK7 <BT>[err] OKTS EEOK7DE EIDAXP OK 7DA/P DEDJ 0 YI G T EIM [err] RST 5 5N 5 5N GK RRRTFE[err] 5T I95NN7[err]EEEEM E[err] Q3EEE /E E 5GE N
```
```text
H B 9? NDE<AS> B TR I G A K
```
```text
E I B8 H B[err]I
```

## Reference — piece tier

### Piece 1 · append

| Token | Meaning |
|---|---|
| `IEPOTA` | [...] POTA: the tail of a call (the recording starts mid-call); POTA = Parks on the Air |
| `K` | over |

**Message:** [...] POTA (Parks on the Air). Over.

### Piece 2 · append

| Token | Meaning |
|---|---|
| `CQ` | general call, any station |
| `POTA` | Parks on the Air: the caller operates from a park and wants park contacts |
| `DE` | from |
| `DP 0YE` | the caller's call sign, damaged on its first sending (?), probably DJ0YI, as the repeat shows |
| `DJ0YI` | call sign DJ0YI, Germany |
| `POTA` | Parks on the Air |
| `K` | over |

**Message:** General call from DJ0YI, activating a park for Parks on the Air (POTA). Over.

### Piece 3 · none

| Token | Meaning |
|---|---|
| `E DEQ` | CQ (?), the general call, damaged |
| `POTA` | Parks on the Air |
| `DE` | from |
| `DJ0YI` | call sign DJ0YI, Germany |
| `DJ0YI` | (repeated) |
| `POTA` | Parks on the Air |
| `K` | over |

**Message:** — (the same POTA call again: section 3 counts a repeat)

### Piece 4 · append

| Token | Meaning |
|---|---|
| `TTK7 DA/P` | OK7DA/P (?), a station answering, damaged: OK7DA/P is Czechia, `/P` = portable |
| `AGN` | again (please repeat) |
| `DE` | from |
| `O NI 7` | [...] damaged, possibly OK7 (?) |
| `<BT>[err]` | <BT> break (a pause in the text) and an unknown code |
| `OK7` | OK7…, the start of the answering call sign |
| `<BT>[err]` | break and an unknown code |
| `OKTS EEOK7DE EIDAXP` | [...] damaged repeats of the answering call sign (?) |
| `OK 7DA/P` | OK7DA/P, Czechia, portable |
| `DEDJ 0 YI` | DE DJ0YI: from DJ0YI (run together and split) |
| `G T EIM [err]` | [...] unreadable (perhaps a greeting) |
| `RST 5 5N 5 5N` | RST 559, sent twice: 5-5-N with N = 9 (cut number); a spurious space each time |
| `GK` | [...] probably BK (?), back to you |
| `RRRTFE[err]` | R R…: roger, then unreadable (the weaker station's reply) |
| `5T I95NN7[err]EEEEM E[err]` | [...] mostly unreadable; 5NN (599) inside it (?) |
| `Q3EEE /E E 5GE N` | [...] unreadable |

**Message:** OK7DA/P (portable, Czechia) answers; DJ0YI asks for it again, then replies: OK7DA/P from
DJ0YI, [...] your report is 559 (sent twice), back to you (?). OK7DA/P's reply is weak: roger, [...] 599
(?), the rest unreadable.

### Piece 5 · append

| Token | Meaning |
|---|---|
| `H B 9?` | HB9? (?), perhaps a partial call sign being asked for; HB9 is a Swiss prefix |
| `NDE<AS>` | DE (from) after a fragment N (?), then <AS>, wait |
| `B TR I G A` | [...] unreadable |
| `K` | over |

**Message:** [...] possibly asking a station starting HB9 (Switzerland) to repeat (?) [...] Over.

### Piece 6 · none

| Token | Meaning |
|---|---|
| `E I B8 H B[err]I` | [...] unreadable; the recording ends |

**Message:** — (nothing readable)

## Reference — session tier

The bar for **section 4**, drafted by Claude Opus 5.5 with `poc/explain_session.py` (2026-10-04, effort low) and lightly edited; the report corrected to 559 after the v0.2 eval run (SRUTI-007).

> Вітаю, ви впіймали **активацію парку**: німецький радіоаматор DJ0YI працює з природоохоронної території і кличе всіх охочих. На його виклик відповідає принаймні одна станція, схоже чеська, і вони обмінюються рапортами. Сигнал місцями поганий, тому значна частина тексту рветься на уламки.
>
> Приблизний переклад:
>
> «...[POTA], прийом.»
>
> «Загальний виклик, активація парку, тут DJ0YI, прийом.» (На початку декодер видав «DP 0YE». Найімовірніше, це той самий DJ0YI, прочитаний з помилками, але це лише моє припущення.)
>
> «Загальний виклик, активація парку, тут DJ0YI, прийом.»
>
> Далі йде найплутаніший шматок. Наскільки можна розібрати, хтось кличе як OK7DA/P. Позивний складається з уламків «OK7», «DA/P», «OK7DA/P», тому я не певен, що прочитав його правильно. Звучить «AGN», тобто прохання повторити. Потім: «...тут DJ0YI... рапорт 559, 559... прийняв, прийняв...». Решта цього фрагмента нечитабельна: [...].
>
> «HB9? Тут... [...], прийом.» Схоже, DJ0YI питає швейцарську станцію, яка його кликала, але її позивний не прийнявся. Чи можна вважати уривок «TR I G A» частиною цього позивного, сказати неможливо.
>
> Останній фрагмент, «E I B8 H B…I», нечитабельний: [...]. Можливо, це знову уламки швейцарського позивного, але це лише здогадка.
>
> Кілька пояснень:
>
> - **Позивні.**
>   - DJ0YI: префікс DJ означає Німеччину.
>   - OK7DA/P: префікс OK означає Чехію, а /P означає, що станція працює в похідних умовах, «портативно».
>   - HB9 означає Швейцарію, але повного позивного в записі немає.
> - **POTA** — програма «Parks on the Air» («Парки в ефірі»): оператори виходять в ефір з природних парків і заповідників, а інші ловлять їх для свого заліку.
> - **Скорочення:**
>   - CQ означає загальний виклик «відгукніться всі».
>   - DE означає «від», «тут».
>   - K означає «прийом, передавай».
>   - AGN означає «ще раз, повтори».
>   - R (RRR) означає «прийняв».
>   - RST — це рапорт про сигнал: розбірливість, сила, тон.
>   - 5 5N — це рапорт «559», записаний скороченими цифрами (N означає 9): розбірливість 5, сила 5, тон 9.
>   - 5NN у відповіді слабшої станції — «599», найкраща оцінка.
>   - Позначки на зразок <BT> та <AS> декодер ставить на службові знаки. Тут вони, найімовірніше, з'явилися через помилки розпізнавання, а не були передані навмисно.
>
> Тож це не неспішна бесіда, а швидка робота з природи: короткі виклики, рапорт і наступний кореспондент.

## What the decoder got wrong

| Decoded | Intended | Note |
|---|---|---|
| `DP 0YE` | `DJ0YI` | first sending damaged; J/P and I/E differ by one element |
| `E DEQ` | `CQ` (?) | the general call, damaged |
| `TTK7 DA/P`, `OK 7DA/P` | `OK7DA/P` | `TT` is `O` broken in two; a spurious space in the call |
| `DEDJ 0 YI` | `DE DJ0YI` | run together, then split |
| `RST 5 5N 5 5N` | `RST 55N 55N` = 559 | spurious spaces; not 5NN — N (-.) never decodes as 5 (.....) |
| piece 4 tail, pieces 5–6 | — | the weaker station: mostly unreadable, must be marked, not guessed |

## Ambiguity a good answer keeps open

- `DP 0YE` is almost certainly DJ0YI's first sending, but an answer must say it is reading it so.
- `H B 9?` may be a partial Swiss call sign being queried, or just damage; an answer must not invent a
  station.
- The answering call sign appears as `OK7DA/P` once cleanly; its other forms are damaged copies, not other
  stations.

## The bar for a passing answer

- Says what POTA is (Parks on the Air: DJ0YI operates from a park) and that it is a CQ call.
- Copies DJ0YI and OK7DA/P exactly, explains `/P` (portable), `CQ`, `DE`, `K`, `AGN`, `RST`, the report 559 (`5 5N`, cut number N = 9) without turning it into 599,
  `<BT>`, `<AS>`.
- Collapses the repeated CQ (piece 3 adds nothing new).
- Marks the weak station's replies as unreadable instead of inventing them.
- Calls it a short contact: a park activator logging a chaser.
