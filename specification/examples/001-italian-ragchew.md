# Example 001 — Italian ragchew

**Source:** KiwiSDR CW decoder output supplied by the author, 2026-10-02; receiver and frequency not recorded. Two or three Italian operators in a slow, friendly conversation.

## Raw decoder output

```
T E TTEAEANDE CAMBIO ANCHE IL RTX ET ACCENDO L' IC 7300
```
```
 ALESORA TI RIP ASS O IL CAMB IO  IU3 F E JDE IZ4PHG  HW K R QSO DE IU2PEJ GRAZIE PER LE INFTA EIO ORSE NON UAI CFE NON [err]T ANTO CH
```
```
E FACCIO CW MA IL MIO MAESTRO [err]L INO CIRCA 7 ANNI HO COMOS[err]IUNO IL GRANDE LINO ET LUI MI HA PRESO SOT T O LA SUA AAEA ET PE R
```

## Reference answer — Claude Fable 5.1

This is the bar for **section 4** (the on-demand, whole-session explanation, in Ukrainian). The piece
tier's outputs for the same text — the section-2 word-by-word gloss and the section-3 English message —
are judged on the same substance: the mapping of every abbreviation this answer explains, and the
translated message it contains, rendered in English.

> Вітаю, ви впіймали живу розмову італійських радіоаматорів. Вони спілкуються звичайною італійською мовою, а декодер місцями помиляється з пробілами та літерами, тому текст виглядає порваним.
>
> Приблизний переклад такий:
>
> > «...і ще міняю трансивер та вмикаю IC-7300.»
> >
> > «Тож повертаю тобі слово, IU3F..., це IZ4PHG, як приймаєш? Прийом.»
> >
> > «Прийняв. Це IU2PEJ, дякую за інформацію. Ти, мабуть, не знаєш, що я не так давно працюю телеграфом, але мій учитель Ліно... років сім тому я познайомився з великим Ліно, і він узяв мене під своє крило, і...»
>
> Кілька пояснень до того, що ви бачите. IZ4PHG, IU2PEJ та IU3F... це позивні операторів: літера I означає Італію, а цифра вказує на регіон (2 це Ломбардія, 3 це північний схід, 4 це Емілія-Романья). IC-7300 це популярний трансивер фірми Icom. Решта це стандартні телеграфні скорочення: DE означає «від», K означає «прийом, передавай», R означає «прийняв», HW це запитання «як чуєш?», QSO це сам сеанс зв'язку, RTX це трансивер, а ET в італійців замінює сполучник «і».
>
> Тобто це не короткий обмін рапортами, а неспішна дружня бесіда кількох людей по колу, і один із них розповідає, як навчився морзянки у свого наставника.

## What the decoder got wrong

| Decoded | Intended | Note |
|---|---|---|
| `ALESORA` | `ALLORA` | "so, then" |
| `RIP ASS O`, `CAMB IO`, `SOT T O` | `RIPASSO`, `CAMBIO`, `SOTTO` | words split by spurious spaces |
| `IU3 F E JDE` | `IU3FEJ DE` (?) | call sign and `DE` run together |
| `INFTA` | `INFO` | |
| `ORSE` | `FORSE` | first letter lost |
| `UAI` | `SAI` | `S` and `U` differ by one element |
| `CFE` | `CHE` | `F` and `H` differ by one element |
| `[err]` | `È` | accented letter outside standard Morse; fits both places: "NON È TANTO", "MAESTRO È LINO" |
| `COMOS[err]IUNO` | `CONOSCIUTO` | |
| `AAEA` | `ALA` | "under his wing" |
| `ET` | `E` | Italian CW habit: `ET` for "and", because `E` (one dot) is easily lost |
| `T E TTEAEANDE` | — | unreadable; must be marked, not guessed |

## Ambiguity a good answer keeps open

`IU3F…` and `IU2PEJ` may be two stations (a round table — the reference answer's reading) or one call sign decoded two ways: they differ by one element in two letters. An answer must not silently merge or invent call signs.

## The bar for a passing answer

- Translates rather than echoes; the output reads naturally (Ukrainian for the section-4 explanation,
  English for the section-3 message).
- Gets the substance: switching to an IC-7300 and handing over; thanks for the information; new to CW; taught by Lino, whom he met about seven years ago and who "took him under his wing".
- Explains `DE`, `K`, `R`, `HW`, `QSO`, `RTX`, `ET`, `CAMBIO`, and the structure of Italian call signs.
- Marks the unreadable start instead of inventing it.
- Calls it a friendly conversation, not a report exchange.

## Known failures

- `qwen3:8b`, thinking off (2026-10-02, against the earlier two-field schema): the translation echoed the
  Italian instead of translating; the summary read `IU3 F E JDE` as one call sign and "il grande Lino" as
  "a great line".
