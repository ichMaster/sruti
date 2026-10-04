#!/usr/bin/env python3
"""v0.2: the session tier over one golden example — the whole session in, a Ukrainian explanation out.

Sends the glossary and every piece of a golden example to Claude Opus 5.5 and prints the explanation,
in the style of example 001's reference answer. Used to draft the reference explanations of new golden
examples; the owner reviews them before they become the bar. A paid call (~$0.03): run it only when the
owner asks.

    uv run --no-project --with anthropic python poc/explain_session.py specification/examples/002-pota-dj0yi.md
    python3 poc/explain_session.py --dry-run specification/examples/002-pota-dj0yi.md   # the prompt, no call

The key is read from .env (ANTHROPIC_API_KEY) and handed to the SDK client; it never goes into argv,
output or a URL.
"""

import argparse
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
GLOSSARY = (ROOT / "glossary" / "cw.md").read_text(encoding="utf-8")
STYLE = ROOT / "specification" / "examples" / "001-italian-ragchew.md"
MODEL = "claude-opus-5-5"
PRICE_IN, PRICE_OUT = 4.0, 20.0  # USD per million tokens (ARCHITECTURE §The two tiers)

SYSTEM = """You are the session explainer of sruti, a CW (Morse) listening agent.
The user listened to amateur-radio CW through a web receiver; a decoder turned it into text, piece by
piece. Explain the whole session to the user IN UKRAINIAN.

Rules — all of them hard:
- Never invent. Unreadable text stays [...]; say a passage is unreadable rather than guess it.
- Copy call signs exactly as sent. Never "correct" one into a different call sign. If fragments may be
  one call sign, or two call signs may be one station decoded twice, say so plainly.
- Decoders drop, split and merge letters; reconstruct a word only when context makes it clear, and say
  it is a reconstruction.

What to write, in plain Ukrainian prose for a curious non-specialist:
1. What the user caught: who is on the air and what kind of exchange it is (a CQ call, a contest run,
   a park activation, a friendly conversation, a beacon).
2. An approximate translation of what was said, in «guillemets», with CW repetitions collapsed.
3. The call signs (country, and region where the digit tells it), and every abbreviation, Q-code,
   prosign and number convention that appears, briefly.
4. One closing line on the character of the exchange.
"""


def golden_pieces(path: pathlib.Path) -> list[str]:
    """The fenced blocks under `## Pieces`, in order, exactly as written."""
    text = path.read_text(encoding="utf-8")
    section = text.split("\n## Pieces", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"```(?:text)?\n(.*?)\n```", section, flags=re.DOTALL)


def style_example() -> str:
    text = STYLE.read_text(encoding="utf-8")
    section = text.split("\n## Reference — session tier", 1)[1].split("\n## ", 1)[0]
    return "\n".join(line[2:] if line.startswith("> ") else line.lstrip(">") for line in section.splitlines()
                     if line.startswith(">")).strip()


def build_prompt(path: pathlib.Path) -> tuple[str, str]:
    pieces = golden_pieces(path)
    system = (SYSTEM + "\nThe style to match — the reference answer for another session:\n\n" + style_example()
              + "\n\nGLOSSARY:\n" + GLOSSARY)
    user = "THE SESSION — decoded pieces, oldest first:\n\n" + "\n".join(
        f"{n}. {p.strip()}" for n, p in enumerate(pieces, 1))
    return system, user


def env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            if value[:1] in ("'", '"'):
                return value[1:].split(value[0], 1)[0]
            return value.split(" #", 1)[0].split("\t#", 1)[0].strip()
    raise SystemExit(f"{name} is not set in .env")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("example", help="a golden example under specification/examples/")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and exit, no call")
    args = ap.parse_args()
    path = pathlib.Path(args.example)
    system, user = build_prompt(path)
    if args.dry_run:
        print(system, "\n\n----- user -----\n", user, sep="")
        return 0

    import anthropic

    client = anthropic.Anthropic(api_key=env_value("ANTHROPIC_API_KEY"))
    t0 = time.monotonic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": "low"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    seconds = time.monotonic() - t0
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    cost = (usage.input_tokens * PRICE_IN + usage.output_tokens * PRICE_OUT) / 1e6
    print(text)
    print(f"\n[{MODEL} · {seconds:.1f} s · {usage.input_tokens} in / {usage.output_tokens} out tokens"
          f" · ${cost:.4f}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
