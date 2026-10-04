#!/usr/bin/env python3
"""v0.1: every message type in the raw captures, checked against ARCHITECTURE §The receiver.

Lists each message type that crossed the audio channel (`SET <name>` sent, `MSG <name>` received, the
greeting), how often and an example, and whether the receiver message table names it. Exits 1 if a
type is missing from the table.

    python3 poc/receiver/inventory.py specification/examples/recordings/*.jsonl
"""

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

ARCHITECTURE = pathlib.Path(__file__).resolve().parents[2] / "specification" / "ARCHITECTURE.md"


def message_names(msg: str) -> list[str]:
    tag, _, body = msg.partition(" ")
    if tag == "SET":
        return [f"SET {body.split(' ')[0].split('=')[0]}"]
    if tag == "MSG":
        return [f"MSG {pair.split('=', 1)[0]}" for pair in body.split(" ") if pair]
    if tag == "SERVER":
        return ["SERVER DE CLIENT"]
    return [tag]


def documented_names() -> set[str]:
    """Names in backticks inside the receiver section's message table."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split("## The receiver", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith(("| →", "| ←"))]
    names = set()
    for row in rows:
        for code in re.findall(r"`([^`]+)`", row):
            words = code.replace("\\|", "|").split(" ")
            if words[0] in ("SET", "MSG", "SERVER"):
                names.add(" ".join(words[:3]) if words[0] == "SERVER" else f"{words[0]} {words[1].split('=')[0]}")
            elif re.fullmatch(r"[A-Za-z_]+", words[0]):
                names.add(f"MSG {words[0]}")  # a bare name continues the row's MSG list
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("captures", nargs="+", help="JSONL captures written by cw_spike.py")
    args = ap.parse_args()
    counts: Counter = Counter()
    examples: dict[str, str] = {}
    for path in args.captures:
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            for name in message_names(rec["msg"]):
                key = f"{rec['dir']} {name}"
                counts[key] += 1
                examples.setdefault(key, rec["msg"][:80])
    documented = documented_names()
    missing = 0
    for key in sorted(counts, key=lambda k: (k[0], k)):
        name = key[2:]
        ok = name in documented
        missing += not ok
        print(f"{'ok ' if ok else 'NEW'} {counts[key]:5}  {key:34} {examples[key]}")
    print(f"\n{len(counts)} message types, {missing} not in ARCHITECTURE §The receiver", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
