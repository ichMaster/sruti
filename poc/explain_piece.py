#!/usr/bin/env python3
"""v0.2 PoC: the piece-explainer contract over example 001, and the prompt the eval uses.

Feeds the three recorded pieces one by one, maintaining the section-3 state between calls,
exactly as the agent will: glossary + last raw pieces + recent section-3 entries + new piece
-> {gloss, action, message|rebuilt}. Prints each answer and the latency.

Usage: python3 poc/explain_piece.py --model qwen3.5:9b [--no-glossary]
       python3 poc/explain_piece.py --model gemini-2.5-flash [--no-glossary]
Stdlib only. Ollama models go to localhost:11434; gemini-* models go to the Gemini API with
GEMINI_API_KEY read from .env (a paid call — for comparisons only, never part of the agent).
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
GLOSSARY = (ROOT / "glossary" / "cw.md").read_text(encoding="utf-8")
HINTS = (ROOT / "glossary" / "cw-hints.md").read_text(encoding="utf-8")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            if value[:1] in ("'", '"'):
                return value[1:].split(value[0], 1)[0]
            return value.split(" #", 1)[0].split("\t#", 1)[0].strip()
    raise SystemExit(f"{name} is not set in .env")

# Example 001 — the three recorded decoder blocks, as pieces.
PIECES = [
    "T E TTEAEANDE CAMBIO ANCHE IL RTX ET ACCENDO L' IC 7300",
    (" ALESORA TI RIP ASS O IL CAMB IO  IU3 F E JDE IZ4PHG  HW K R QSO DE IU2PEJ GRAZIE PER LE "
     "INFTA EIO ORSE NON UAI CFE NON [err]T ANTO CH"),
    ("E FACCIO CW MA IL MIO MAESTRO [err]L INO CIRCA 7 ANNI HO COMOS[err]IUNO IL GRANDE LINO ET "
     "LUI MI HA PRESO SOT T O LA SUA AAEA ET PE R"),
]

SYSTEM_HEAD = """You are the piece explainer of sruti, a CW (Morse) listening agent.
You receive decoded CW text from amateur-radio conversations. Decoders drop, split and merge
letters; operators use CW abbreviations, Q-codes and prosigns.

Rules — all of them hard:
- Never invent. Unreadable text is rendered as [...]. A call sign is copied exactly as sent and
  never "corrected" into a different one; never offer a call sign that is not in the text. If two
  readings are possible, say so briefly.
"""

RULE_WITH_GLOSSARY = (
    "- Expand tokens ONLY against the glossary. Unknown token -> keep it as sent and mark it (?).\n"
)
RULE_WITHOUT_GLOSSARY = (
    "- Expand abbreviations from your knowledge of amateur-radio CW. If you are not sure of a\n"
    "  token, keep it as sent and mark it (?).\n"
)
RULE_WITH_HINTS = (
    "- Use your own knowledge of amateur-radio CW and of the operators' language; translate plain\n"
    "  words normally. The HINTS below list what models commonly get wrong: follow them. Rebuild a\n"
    "  damaged word when context makes it clear and say it is a reconstruction; if you are not sure\n"
    "  of a token, keep it as sent and mark it (?).\n"
)

SYSTEM_BODY = """- The operators' language may be Italian, German, English etc. Translate MEANING into English.
- gloss: map the raw text token by token (words, abbreviations, Q-codes, prosigns, call signs),
  in order, every token covered. Repeats stay in the gloss.
- message: what the operator actually SAID, as one natural English message. Collapse CW
  repetitions (CQ CQ CQ -> one general call; a doubled call sign -> once). Add nothing. A call sign
  you joined from fragments keeps its (?) in the message too.
- action: "none" if this piece adds nothing new for the reader beyond repeating what the recent
  entries already say; "append" if it adds something (message = the new entry; a correction of an
  earlier entry is also an append, phrased "correction: ..."); "rebuild" ONLY if the new piece
  reframes what the recent entries say (then rebuilt = replacement list for those entries). A rebuild
  that would leave the entries saying the same thing is wrong: that is "none".
"""


def build_system(glossary: str) -> str:
    if glossary == "full":
        return SYSTEM_HEAD + RULE_WITH_GLOSSARY + SYSTEM_BODY + f"\nGLOSSARY:\n{GLOSSARY}\n"
    if glossary == "hints":
        return SYSTEM_HEAD + RULE_WITH_HINTS + SYSTEM_BODY + f"\nHINTS:\n{HINTS}\n"
    return SYSTEM_HEAD + RULE_WITHOUT_GLOSSARY + SYSTEM_BODY

SCHEMA = {
    "type": "object",
    "properties": {
        "gloss": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "meaning": {"type": "string"},
                },
                "required": ["token", "meaning"],
            },
        },
        "action": {"type": "string", "enum": ["none", "append", "rebuild"]},
        "message": {"type": ["string", "null"]},
        "rebuilt": {"type": ["array", "null"], "items": {"type": "string"}},
    },
    "required": ["gloss", "action"],
}

# The same contract in the OpenAPI subset the Gemini API takes for responseSchema.
GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "gloss": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "token": {"type": "STRING"},
                    "meaning": {"type": "STRING"},
                },
                "required": ["token", "meaning"],
                "propertyOrdering": ["token", "meaning"],
            },
        },
        "action": {"type": "STRING", "enum": ["none", "append", "rebuild"]},
        "message": {"type": "STRING", "nullable": True},
        "rebuilt": {"type": "ARRAY", "items": {"type": "STRING"}, "nullable": True},
    },
    "required": ["gloss", "action"],
    "propertyOrdering": ["gloss", "action", "message", "rebuilt"],
}


def build_user(context: list[str], section3: list[str], piece: str) -> str:
    return (
        "PREVIOUS RAW PIECES (ground truth, oldest first):\n"
        + ("\n".join(f"- {p}" for p in context) if context else "(none — session start)")
        + "\n\nRECENT SECTION-3 ENTRIES (what the reader has been told):\n"
        + ("\n".join(f"{n}. {e}" for n, e in enumerate(section3, 1)) if section3 else "(empty)")
        + f"\n\nNEW PIECE:\n{piece}\n"
    )


def call(model: str, system: str, user_msg: str, timeout: float) -> tuple[dict, float, dict]:
    if model.startswith("gemini-"):
        return call_gemini(model, system, user_msg, timeout)
    return call_ollama(model, system, user_msg, timeout)


def call_gemini(model: str, system: str, user_msg: str, timeout: float) -> tuple[dict, float, dict]:
    config = {"responseMimeType": "application/json", "responseSchema": GEMINI_SCHEMA}
    if model.startswith("gemini-3"):
        # Gemini 3.x cannot turn thinking off; low is the minimum. Google advises the default temperature.
        config["thinkingConfig"] = {"thinkingLevel": "low"}
    else:
        config["temperature"] = 0.2
        config["thinkingConfig"] = {"thinkingBudget": 0}
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        "generationConfig": config,
    }).encode()
    req = urllib.request.Request(
        GEMINI_URL.format(model=model), data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": env_value("GEMINI_API_KEY")},
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.load(resp)
    dt = time.monotonic() - t0
    usage = out.get("usageMetadata", {})
    stats = {
        "provider": "gemini",
        "prompt_tokens": usage.get("promptTokenCount", 0),
        "out_tokens": usage.get("candidatesTokenCount", 0),
        "thought_tokens": usage.get("thoughtsTokenCount", 0),
    }
    text = out["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text), dt, stats


def call_ollama(model: str, system: str, user_msg: str, timeout: float) -> tuple[dict, float, dict]:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "format": SCHEMA,
        "think": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
        "keep_alive": "15m",
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.load(resp)
    dt = time.monotonic() - t0
    stats = {
        "prompt_tokens": out.get("prompt_eval_count", 0),
        "prompt_s": out.get("prompt_eval_duration", 0) / 1e9,
        "out_tokens": out.get("eval_count", 0),
        "out_s": out.get("eval_duration", 0) / 1e9,
        "load_s": out.get("load_duration", 0) / 1e9,
    }
    return json.loads(out["message"]["content"]), dt, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--gloss-rows", type=int, default=100, help="gloss rows to print per piece")
    ap.add_argument("--glossary", choices=["full", "hints", "none"], default="full",
                    help="full = glossary/cw.md, hints = glossary/cw-hints.md, none = no glossary")
    ap.add_argument("--no-glossary", action="store_true", help="same as --glossary none")
    args = ap.parse_args()

    mode = "none" if args.no_glossary else args.glossary
    system = build_system(mode)
    sizes = {"full": len(GLOSSARY), "hints": len(HINTS), "none": 0}
    print(f"model: {args.model} · glossary: {mode} ({sizes[mode]} chars) · pieces: {len(PIECES)}")
    section3: list[str] = []
    latencies: list[float] = []

    for i, piece in enumerate(PIECES, 1):
        user = build_user(PIECES[max(0, i - 6):i - 1], section3, piece)
        try:
            ans, dt, st = call(args.model, system, user, args.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:600]
            print(f"\n--- piece {i}: FAILED: HTTP {exc.code}: {detail}")
            continue
        except Exception as exc:  # noqa: BLE001 - PoC: report and continue
            print(f"\n--- piece {i}: FAILED after error: {exc}")
            continue
        latencies.append(dt)

        action = ans.get("action")
        print(f"\n--- piece {i} · {dt:.1f}s · action={action}")
        if st.get("provider") == "gemini":
            print(f"    prompt {st['prompt_tokens']} tok · output {st['out_tokens']} tok"
                  f" · thinking {st['thought_tokens']} tok · wall clock incl. network"
                  f" ({st['out_tokens'] / dt:.0f} out tok/s overall)")
        elif st["out_s"]:
            print(f"    load {st['load_s']:.1f}s · prompt {st['prompt_tokens']} tok in {st['prompt_s']:.1f}s"
                  f" · output {st['out_tokens']} tok in {st['out_s']:.1f}s"
                  f" ({st['out_tokens'] / st['out_s']:.1f} tok/s)")
        print(f"raw: {piece.strip()}")
        for row in (ans.get("gloss") or [])[: args.gloss_rows]:
            print(f"  {row.get('token', '?'):>14}  —  {row.get('meaning', '?')}")
        if action == "append" and ans.get("message"):
            section3.append(ans["message"])
        elif action == "rebuild" and ans.get("rebuilt"):
            section3 = list(ans["rebuilt"])
        print("section 3 now:")
        for n, e in enumerate(section3, 1):
            print(f"  {n}. {e}")

    if latencies:
        print(f"\nlatency: first {latencies[0]:.1f}s (cold) · "
              f"rest avg {sum(latencies[1:]) / len(latencies[1:]):.1f}s" if len(latencies) > 1
              else f"\nlatency: {latencies[0]:.1f}s (single call)")
        print("budget: 5.0s per piece (warm) — ARCHITECTURE §The two tiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
