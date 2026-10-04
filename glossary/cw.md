# CW glossary

Versioned data rendered verbatim into both model prompts (ARCHITECTURE.md §Components). Entries are
`TOKEN — meaning`. The models must never expand a token against this file; an unknown token is explained
as unknown, not guessed.

## Prosigns (sent as one sign; end-of-turn markers cut pieces)

- K — over; any station may reply
- KN — over, only the named station
- BK — break; quick back-and-forth without call signs
- AR — end of message
- SK — end of contact (also written VA)
- AS — wait, stand by
- CL — closing the station, going off air
- CT / KA — attention, transmission starts

## Q-codes

- QRG — exact frequency
- QRL — the frequency is busy / are you busy?
- QRM — man-made interference
- QRN — static, atmospheric noise
- QRO — increase power / high power
- QRP — reduce power / low power (also: a low-power station)
- QRQ — send faster
- QRS — send slower
- QRT — stop transmitting, shutting down
- QRU — I have nothing for you
- QRV — I am ready
- QRX — wait, stand by (QRX 5 = back in 5 minutes)
- QRZ — who is calling me?
- QSB — fading signal
- QSL — I confirm reception (also: the confirmation card)
- QSO — a contact, a conversation
- QSY — change frequency
- QTC — I have a message for you
- QTH — my location is
- QTR — the exact time

## Common abbreviations

- ABT — about
- ADR — address
- AGN — again
- ANT — antenna
- BCNU — be seeing you
- BTU — back to you
- C — yes, correct
- CFM — confirm
- CONDX — (propagation) conditions
- CPY / CPI — copy
- CQ — general call: anyone, come in
- CU — see you
- CUAGN — see you again
- CUL — see you later
- CW — Morse telegraphy
- DE — from (this is)
- DR — dear
- DX — long distance, a rare / distant station
- ES — and
- FB — fine business: excellent
- FER — for
- GA — good afternoon / go ahead
- GB — goodbye / God bless
- GE — good evening
- GL — good luck
- GM — good morning
- GN — good night
- GND — ground
- GUD — good
- HAM — amateur radio operator
- HI — laughter
- HPE — hope
- HR — here
- HV — have
- HW — how (HW? / HW CPY? = how do you copy?)
- INFO — information
- KW — kilowatt
- LID — a poor operator
- LW — long-wire antenna
- MNI — many
- MSG — message
- N — no / the digit 9 in cut numbers
- NIL — nothing, nothing received
- NR — number / near; NR? = your (serial) number, please?
- NW — now
- OB — old boy
- OC — old chap
- OK — all correct
- OM — old man: a fellow (male) operator
- OP — operator / operator's name
- OT — old timer
- PSE — please
- PWR — power
- R — roger, received
- RCVD — received
- RIG — the transceiver / station equipment
- RPT — repeat / report
- RST — signal report: Readability 1-5, Strength 1-9, Tone 1-9
- RX — receiver
- SIG — signal
- SKED — a scheduled contact
- SRI — sorry
- SSB — single sideband (voice)
- STN — station
- SW — short wave / switch
- TKS / TNX — thanks
- TMW — tomorrow
- TRX / RTX — transceiver
- TU — thank you; in a contest it closes a contact ("TU E72U" = thanks, E72U is ready for the next caller)
- TX — transmitter
- U — you
- UFB — ultra fine business: superb
- UR — your / you are
- VY — very
- WATTS / W — watts
- WID — with
- WKD — worked (made a contact with)
- WL — will / well
- WX — weather
- XCVR — transceiver
- XTAL — crystal
- XYL — wife
- YL — young lady: a female operator
- YR / YRS — year / years
- 5NN — 599: the standard best signal report (cut numbers)
- 73 — best regards (standard sign-off)
- 88 — love and kisses (sign-off between close friends / to a YL)

## Cut numbers (digits shortened in reports)

- T — 0 (5TT = 500)
- N — 9 (5NN = 599)
- A — 1
- E — 5 (rare)

Cut numbers stand only where a report or a contest serial number stands (`T56` = 056, `4T6` = 406,
`15T` = 150). A report is read as sent: `5 5N` (a spurious space) is 559, not 599. A lone letter between
exchanges is a fragment of noise or of a weaker station, not a digit.

## Contests and activations

- TEST — a contest call: "CQ TEST" or "TEST <call>" = calling any station in a contest
- Contest exchange: the running station sends `<call> 5NN <serial>`; the caller replies `TU 5NN <its serial>`
  (sometimes with a club or region tag); `TU` ends the contact. Repeats of the call and of `TEST` carry
  no new content.
- CALL? — your call sign, please?
- POTA — Parks on the Air: an "activator" operates from a park and calls "CQ POTA"; chasers answer
- SOTA — Summits on the Air: the same, from a summit
- /P after a call sign — portable

## Per-language CW habits

- Italian: ET — "e" (and); the single-dot E is easily lost, so operators send ET
- Italian: CAMBIO — over, handing back
- Italian: CIAO — hello / goodbye
- German: AWDH — auf Wiederhören (goodbye)
- German: AWDS — auf Wiedersehen (goodbye)
- French: MCI — merci (thanks)
- Russian/Ukrainian ops: ДСВ/DSW — до свидания (goodbye, sent in transliteration)

## Call signs

Structure: prefix (country) + digit (often a region) + suffix (the operator). A call sign is copied
exactly as sent and never "corrected" into another one. Suffixes after a slash: /P portable, /M mobile,
/MM maritime, /QRP low power, /A alternate location.

Common prefixes:

- I, IZ, IU, IK, IW — Italy (digit = region: 0 Lazio, 1 NW, 2 Lombardy, 3 NE, 4 Emilia-Romagna, 5 Tuscany, 6 centre-east, 7 south-east, 8 south, 9 Sicily/islands)
- DL, DJ, DK, DF, DO — Germany
- F — France
- G, M, 2E — England
- EA — Spain; CT — Portugal
- ON — Belgium; PA — Netherlands; LX — Luxembourg
- HB9 — Switzerland; OE — Austria
- OK — Czechia; OM — Slovakia (as a prefix; OM is also "old man" in text)
- SP — Poland; HA/HG — Hungary
- UR, UT, US, UX, UW, EM — Ukraine
- EW — Belarus; R, RA, UA — Russia
- YL — Latvia (as a prefix; YL is also "young lady" in text); LY — Lithuania; ES — Estonia (ES is also "and" in text)
- OH — Finland; SM — Sweden; LA — Norway; OZ — Denmark
- EI — Ireland; SV — Greece; 9A — Croatia; S5 — Slovenia; LZ — Bulgaria; YO — Romania; E7 — Bosnia; 4O — Montenegro; Z3 — North Macedonia
- TA — Türkiye; 4X, 4Z — Israel; JY — Jordan
- K, W, N, AA–AL — USA; VE, VA — Canada; XE — Mexico
- PY — Brazil; LU — Argentina; CE — Chile
- JA–JS — Japan; HL — South Korea; BY — China; VU — India
- VK — Australia; ZL — New Zealand; ZS — South Africa

Ambiguity rule: ES, OM, YL (and similar) are prefixes only in a call-sign position; in running text they
are the abbreviations above. Position decides; when it is genuinely unclear, say so.

## NCDXF/IARU beacons (14.100 MHz, 3-minute cycle, 22 WPM — known call signs)

4U1UN (UN New York) · VE8AT (Canada) · W6WX (USA) · KH6RS (Hawaii) · ZL6B (New Zealand) ·
VK6RBP (Australia) · JA2IGY (Japan) · RR9O (Russia) · VR2B (Hong Kong) · 4S7B (Sri Lanka) ·
ZS6DN (South Africa) · 5Z4B (Kenya) · 4X6TU (Israel) · OH2B (Finland) · CS3B (Madeira) ·
LU4AA (Argentina) · OA4B (Peru) · YV5B (Venezuela)
