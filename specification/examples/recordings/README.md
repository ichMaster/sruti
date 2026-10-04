# Recordings — v0.1

Real receiver audio with its raw capture, the fixtures the fake receiver replays (v1.1) and the decoder is
tuned and regression-tested on (v1.2). All from the owner's receiver, **Trémolat**
(`sdr.autreradioautreculture.com:8073`, KiwiSDR v1.902, 11 m vertical), recorded with the v0.1 spike:

```
uv run --no-project --with numpy python poc/receiver/cw_spike.py --browser-path \
    --receiver sdr.autreradioautreculture.com:8073 --freq <kHz> --seconds <s> \
    --out <name>.jsonl --audio <name>.wav
```

- **`<name>.wav`** — the channel's audio as sent: mono, 16-bit, 12 kHz, CW mode, passband 300–700 Hz,
  `freq` = the signal's own frequency, so the signal sits near a 500 Hz tone.
- **`<name>.jsonl`** — every text message on the socket, `{t, ws, dir, msg}` (ARCHITECTURE §The receiver);
  `client_public_ip` masked, the receiver's configuration blobs reduced to their size.
- Decode one: `uv run --no-project --with numpy python poc/receiver/cw_decode.py <name>.wav`.
- Check the message inventory: `python3 poc/receiver/inventory.py *.jsonl`.

| Recording | Frequency | Recorded | Length | What is on it | Prototype decoder |
|---|---|---|---|---|---|
| `beacons` | 14 100.00 kHz | — | — | *pending: 20 m was closed at dawn; retried as the band opens* | — |
| `cq` | 7 033.05 kHz | 2026-10-03 11:32 UTC | 177 s | DJ0YI (Germany) calling CQ POTA from a park; OK7DA/P (Czechia, portable) answers; RST 5NN | tone 498 Hz, 25 dB, ~18 WPM |
| `conversation` | 7 027.50 kHz | 2026-10-04 05:45 UTC | 238 s | E72U (Bosnia and Herzegovina) running the TRC DX Contest: nine contacts — F6FTI, SP1AEN, YL2TD, LZ3ZZ, YO3GNF, SP3VT, OM3CPF, UW3WU, YO4TL — each `5NN` plus a serial number | tone 498 Hz, 23 dB, ~31 WPM |

## What the prototype decoder reads

Verbatim output of `cw_decode.py` after the v0.1 code review (bias-aware gap thresholds) — the baseline
the v1.2 decoder must match or beat. `[err]` is a code the decoder could not map; errors cluster where the signal fades or a weaker
station transmits.

**`cq`**

```
IEPOTA K CQ POTA DE DP 0YE DJ0YI POTA K E DEQ POTA DE DJ0YI DJ0YI POTA K TTK7 DA/P AGN DE O NI 7
<BT>[err] OK7 <BT>[err] OKTS EEOK7DE EIDAXP OK 7DA/P DEDJ 0 YI G T EIM [err] RST 5 5N 5 5N GK
RRRTFE[err] 5T I95NN7[err]EEEEM E[err] Q3EEE /E E 5GE N H B 9? NDE<AS> B TR I G A K E I B8 H B[err]I
```

Read by a person: `CQ POTA DE DJ0YI DJ0YI POTA K` (twice) · `OK7DA/P` calling, `AGN` (again) · `OK7DA/P DE
DJ0YI … RST 5NN` · the rest is the weaker OK7DA/P and fading.

**`conversation`**

```
IUU E72U EETE I[err] T F6FTI 5NN T56 INA I E [err]E TD I E EI EB NR E E[err] IE IE I F CALL? T EEEIE EE
E E TU E72U SP1AE N SP1AE N DP1AEN 5NN T57 TU 5NN6 16 TRC TU[err]2U YL2TD YL2TD 5NN T58 ? E YL2TD 5NN
T58 TU 5NN 485 TRC TU E72U I TEST E72U E72U TEST E72U E72U [err]Z3ZZ E I ZZ E LZ3ZZ LZ3ZZ 5NN T59 5NN
391 TRC TU NMQSMGNF YO3GNF 5NN T60 A 5NN 1TU ETU E72U SOQU SP3VT E E SP3VT 5NN T61 TU 5NN 4T6 T TU
O[err]KU R UOM3CNF 5NN T62 G M3CPF 5NNE281 E ETU EZ OM3CPF TU EE 4W3WU UW3WU 5NN T63 5NN 15T E E TU
E72U YO4TL YO4TL 5NN T64 M
```

Read by a person: E72U's serials run `T56` … `T64` (`T` is a cut zero: 056 … 064), each contact
`<call> 5NN 0nn`, the caller's reply `5NN <serial> TRC`, then `TU E72U` or `TEST E72U`.
