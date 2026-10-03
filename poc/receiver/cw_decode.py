#!/usr/bin/env python3
"""v0.1 prototype: decode CW from receiver audio on the Mac.

Reads a mono WAV — the KiwiSDR channel audio the spike records — finds the CW tone in the passband,
follows its envelope with an adaptive threshold, measures marks and gaps, adapts to the sending speed,
and turns the Morse into text: prosigns as <AR>, unknown codes as [err], word gaps as spaces.

    uv run --no-project --with numpy python poc/receiver/cw_decode.py var/recordings/tremolat.wav
    uv run --no-project --with numpy python poc/receiver/cw_decode.py --selftest
"""

import argparse
import sys
import wave

import numpy as np

HOP_S = 0.005  # envelope resolution: 5 ms, a fifth of a dot at 48 WPM
WIN_S = 0.012  # envelope smoothing window
TONE_BAND = (300.0, 1000.0)  # the KiwiSDR CW passband is 300-700 Hz; a little margin either side
MIN_TONE_PROMINENCE_DB = 6.0  # a CW tone stands this far above the rest of the passband
LEVEL_WINDOW_S = 4.0  # adaptive threshold: the noise floor and signal peak over this window
MIN_CONTRAST_DB = 14.0  # noise alone spreads ~11 dB between its 25th and 97th percentile
WPM_RANGE = (5.0, 50.0)

MORSE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F", "--.": "G", "....": "H",
    "..": "I", ".---": "J", "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O", ".--.": "P",
    "--.-": "Q", ".-.": "R", "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5", "-....": "6",
    "--...": "7", "---..": "8", "----.": "9",
    ".-.-.-": ".", "--..--": ",", "..--..": "?", "-..-.": "/", ".----.": "'", "-.-.--": "!",
    "---...": ":", "-.-.-.": ";", ".-..-.": '"', ".--.-.": "@", "..--.-": "_", "-....-": "-",
    # prosigns, sent run together
    ".-.-.": "<AR>", "...-.-": "<SK>", "-.--.": "<KN>", "-...-": "<BT>", ".-...": "<AS>",
    "-.-.-": "<KA>", "........": "<HH>",
}


# ---------------------------------------------------------------- signal → keying

def load_wav(path: str) -> tuple[np.ndarray, float]:
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2:
            raise SystemExit(f"{path}: expected 16-bit PCM")
        fs = float(w.getframerate())
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    return x, fs


def find_tone(x: np.ndarray, fs: float, band_hz: tuple[float, float] = TONE_BAND) -> tuple[float, float]:
    """The CW tone and how far (dB) it stands above the rest of the passband.

    Keyed CW is intermittent, so each frequency is scored by its loud moments (the 90th percentile over
    frames), not its average; a carrier then stands out of the flat noise of an empty passband.
    """
    n = 2048
    if len(x) < n:
        n = 1 << max(8, int(np.log2(len(x))))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[:: n // 2]
    power = np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2
    loud = np.percentile(power, 90, axis=0)
    freqs = np.fft.rfftfreq(n, 1 / fs)
    band = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    # Only bins the receiver's filter lets through: the skirts outside its passband are near silent and
    # would drag the median down until plain noise looked like a tone.
    typical = np.median(power, axis=0)
    band &= typical >= typical[band].max() / 100
    peak = int(np.argmax(loud[band]))
    prominence = 10 * np.log10(loud[band][peak] / np.median(loud[band]))
    return float(freqs[band][peak]), float(prominence)


def envelope_db(x: np.ndarray, fs: float, tone: float) -> np.ndarray:
    """Tone magnitude in dB every HOP_S: mix the tone to 0 Hz, average over WIN_S, take |.|."""
    t = np.arange(len(x)) / fs
    base = x * np.exp(-2j * np.pi * tone * t)
    win = max(1, int(WIN_S * fs))
    csum = np.concatenate([[0], np.cumsum(base)])
    smooth = (csum[win:] - csum[:-win]) / win
    hop = max(1, int(HOP_S * fs))
    return 20 * np.log10(np.abs(smooth[::hop]) + 1e-9)


def keying(env: np.ndarray) -> np.ndarray:
    """Key down / up per hop, against a threshold midway between the local floor and peak."""
    w = max(10, int(LEVEL_WINDOW_S / HOP_S))
    step = max(1, w // 8)
    centres = np.arange(0, len(env), step)
    floor = np.empty(len(centres))
    peak = np.empty(len(centres))
    for i, c in enumerate(centres):
        seg = env[max(0, c - w // 2): c + w // 2 + 1]
        floor[i] = np.percentile(seg, 25)
        peak[i] = np.percentile(seg, 97)
    floor = np.interp(np.arange(len(env)), centres, floor)
    peak = np.interp(np.arange(len(env)), centres, peak)
    threshold = floor + 0.5 * (peak - floor)
    has_signal = (peak - floor) >= MIN_CONTRAST_DB
    keys = np.zeros(len(env), dtype=bool)
    down = False
    for i, level in enumerate(env):  # hysteresis of ±1 dB around the threshold
        if not has_signal[i]:
            down = False
        elif down:
            down = level > threshold[i] - 1.0
        else:
            down = level > threshold[i] + 1.0
        keys[i] = down
    return keys


def runs(keys: np.ndarray, min_hops: int = 2) -> list[list]:
    """[key_down, length_in_hops] runs, with glitches shorter than min_hops folded into neighbours."""
    out: list[list] = []
    for k in keys:
        if out and out[-1][0] == bool(k):
            out[-1][1] += 1
        else:
            out.append([bool(k), 1])
    merged: list[list] = []
    for state, length in out:
        if merged and length < min_hops or merged and merged[-1][0] == state:
            merged[-1][1] += length
        else:
            merged.append([state, length])
    return merged


# ---------------------------------------------------------------- keying → text

GLITCH_MARK = 0.4  # a mark shorter than this many dots is a noise spike, part of the gap
DROPOUT_GAP = 0.25  # a gap shorter than this many dots is a fade inside one mark


def _two_means(m: np.ndarray) -> tuple[float, float]:
    a, b = np.percentile(m, 20), np.percentile(m, 80)
    for _ in range(20):
        near_a = np.abs(m - a) <= np.abs(m - b)
        if near_a.all() or (~near_a).all():
            break
        a, b = m[near_a].mean(), m[~near_a].mean()
    return float(min(a, b)), float(max(a, b))


def dot_length(marks: list[int]) -> float:
    """Dot length in hops: the lower of two clusters of mark lengths (dots, dashes ≈ 3 dots).

    Noise spikes form a third, much shorter cluster; when the two clusters are further apart than dots
    and dashes ever are, the lower one is noise and is dropped before trying again.
    """
    lo_hops = 1.2 / WPM_RANGE[1] / HOP_S
    hi_hops = 1.2 / WPM_RANGE[0] / HOP_S
    m = np.log(np.clip(np.asarray(marks, dtype=float), lo_hops * 0.5, hi_hops * 3.5))
    for _ in range(3):
        if len(m) < 2 or np.ptp(m) < 0.4:  # one cluster only: call it dots if short, dashes if long
            guess = float(np.exp(np.median(m)))
            return float(np.clip(guess if guess <= hi_hops else guess / 3, lo_hops, hi_hops))
        a, b = _two_means(m)
        upper = m > (a + b) / 2
        if np.exp(b - a) > 4.5 and upper.sum() >= 4:
            m = m[upper]
            continue
        break
    dot, dash = float(np.exp(a)), float(np.exp(b))
    if dash / dot < 1.8:  # the clusters are not dot/dash: all one kind
        dot = dot if dot <= hi_hops else dot / 3
    return float(np.clip(dot, lo_hops, hi_hops))


def decode(segments: list[list], adapt_marks: int = 24) -> tuple[str, list[float]]:
    """Text, plus the dot length (hops) used along the way. The dot length follows the last marks.

    Marks shorter than GLITCH_MARK dots count as gap (noise spikes); gaps shorter than DROPOUT_GAP dots
    between two marks join them into one (a fade inside a dash).
    """
    marks = [n for k, n in segments if k]
    if not marks:
        return "", []
    dot = dot_length(marks[:adapt_marks] if len(marks) >= 6 else marks)
    recent: list[int] = []
    text, symbol, dots_used = [], "", []
    mark, gap = 0, 0

    def flush_char():
        nonlocal symbol
        if symbol:
            text.append(MORSE.get(symbol, "[err]"))
            symbol = ""

    def commit_mark():
        nonlocal symbol, dot
        if not mark:
            return
        symbol += "." if mark < 2 * dot else "-"
        recent.append(mark)
        if len(recent) >= 8 and len(recent) % 4 == 0:
            dot = dot_length(recent[-adapt_marks:])
        dots_used.append(dot)

    def take_gap():
        if gap >= 5 * dot:  # word gap (7 dots nominal)
            flush_char()
            if text and text[-1] != " ":
                text.append(" ")
        elif gap >= 2 * dot:  # character gap (3 dots nominal)
            flush_char()

    for key_down, n in segments:
        if not key_down or n < GLITCH_MARK * dot:
            gap += n
            continue
        if mark and gap < DROPOUT_GAP * dot:
            mark += gap + n
        else:
            commit_mark()
            take_gap()
            mark = n
        gap = 0
    commit_mark()
    flush_char()
    return "".join(text).strip(), dots_used


# ---------------------------------------------------------------- the whole chain

def decode_audio(x: np.ndarray, fs: float, band_hz: tuple[float, float] = TONE_BAND) -> dict:
    if len(x) < fs:  # under a second of audio: nothing to decode
        return {"text": "", "tone_hz": 0.0, "prominence_db": 0.0, "wpm": 0.0, "seconds": len(x) / fs}
    tone, prominence = find_tone(x, fs, band_hz)
    if prominence < MIN_TONE_PROMINENCE_DB:
        return {"text": "", "tone_hz": tone, "prominence_db": prominence, "wpm": 0.0, "seconds": len(x) / fs}
    env = envelope_db(x, fs, tone)
    segments = runs(keying(env))
    text, dots = decode(segments)
    wpm = 1.2 / (float(np.median(dots)) * HOP_S) if dots else 0.0
    return {"text": text, "tone_hz": tone, "prominence_db": prominence, "wpm": wpm, "seconds": len(x) / fs}


# ---------------------------------------------------------------- self-test on synthetic CW

def synthesize(text: str, wpm: float, fs: float = 12000.0, tone: float = 620.0, snr_db: float = 10.0,
               seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    inverse = {v: k for k, v in MORSE.items()}
    unit = 1.2 / wpm
    pieces = [np.zeros(int(0.8 * fs))]

    def tone_for(seconds):
        t = np.arange(int(seconds * fs)) / fs
        ramp = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.004)  # 4 ms edges, as real keying
        return np.sin(2 * np.pi * tone * t) * ramp

    for word in text.split(" "):
        for ch in word if not word.startswith("<") else [word]:
            for j, sym in enumerate(inverse[ch]):
                pieces.append(tone_for(unit if sym == "." else 3 * unit))
                if j < len(inverse[ch]) - 1:
                    pieces.append(np.zeros(int(unit * fs)))
            pieces.append(np.zeros(int(3 * unit * fs)))
        pieces.append(np.zeros(int(4 * unit * fs)))
    pieces.append(np.zeros(int(0.8 * fs)))
    clean = np.concatenate(pieces) if text else np.zeros(int(20 * fs))
    noise = rng.normal(0, 10 ** (-snr_db / 20) / np.sqrt(2), len(clean))
    spectrum = np.fft.rfft(clean + noise)  # the receiver's 300-700 Hz CW passband
    freqs = np.fft.rfftfreq(len(clean), 1 / fs)
    spectrum[(freqs < 300) | (freqs > 700)] *= 0.01
    return (np.fft.irfft(spectrum, len(clean)) * 8000).astype(np.float32)


def selftest() -> int:
    cases = [
        ("CQ CQ DE IZ4PHG IZ4PHG K", 22, 10.0),
        ("R R TNX FER RPT UR RST 5NN 5NN <BT> NAME LINO <KN>", 18, 8.0),
        ("TEST DE OH2B 73 <SK>", 28, 12.0),
        ("CAMBIO ANCHE IL RTX ET ACCENDO IC 7300 K", 14, 6.0),
        ("", 20, 0.0, TONE_BAND),  # an empty passband: noise only, nothing may be decoded
        ("", 20, 0.0, (200.0, 2800.0)),  # the same, searched wider than the receiver's filter
        ("CQ CQ DE IZ4PHG IZ4PHG K", 22, 10.0, (200.0, 2800.0)),
    ]
    failed = 0
    for text, wpm, snr, *band in cases:
        got = decode_audio(synthesize(text, wpm, snr_db=snr), 12000.0, *band)
        ok = got["text"] == text
        failed += not ok
        print(f"{'ok ' if ok else 'BAD'} {wpm:>2} WPM, SNR {snr:4.1f} dB → {got['wpm']:4.1f} WPM, "
              f"tone {got['tone_hz']:.0f} Hz: {got['text']!r}" + ("" if ok else f"  (want {text!r})"))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("wav", nargs="?", help="mono 16-bit WAV of the receiver audio")
    ap.add_argument("--selftest", action="store_true", help="decode synthetic CW with known text")
    ap.add_argument("--band", default=f"{TONE_BAND[0]:.0f}-{TONE_BAND[1]:.0f}",
                    help="audio band to search for the tone, Hz (default %(default)s)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.wav:
        ap.error("give a WAV file or --selftest")
    x, fs = load_wav(args.wav)
    lo, hi = (float(v) for v in args.band.split("-"))
    r = decode_audio(x, fs, (lo, hi))
    print(r["text"] or "(no CW found)")
    print(f"\n[{r['seconds']:.0f} s · tone {r['tone_hz']:.0f} Hz, {r['prominence_db']:.1f} dB above the passband"
          f" · ~{r['wpm']:.0f} WPM]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
