#!/usr/bin/env python3
"""v0.2: run the piece explainer over the golden examples and report against the references.

Feeds each golden example's pieces in order — the last 5 raw pieces, the recent section-3 entries and the
new piece — exactly as the agent will, applies none / append / rebuild to section 3, checks each answer
automatically, and writes a side-by-side report (model vs reference) under poc/eval/.

    python3 poc/eval_golden.py --selftest                      # offline, canned answers
    python3 poc/eval_golden.py --live --glossary hints         # real Gemini calls (paid, opt-in)
    python3 poc/eval_golden.py --live --glossary full --examples 002,003

The prompt and the Gemini call are poc/explain_piece.py's, so there is one prompt to settle. The key is
read from .env and sent only in the x-goog-api-key header.
"""

import argparse
import datetime
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import explain_piece

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "specification" / "examples"
REPORTS = ROOT / "poc" / "eval"
CONTEXT_PIECES = 5  # raw pieces shown with the new one (ARCHITECTURE §The two tiers)
RECENT_ENTRIES = 5  # section-3 entries shown; a rebuild replaces exactly these
BUDGET_S = 5.0
PRICE_IN, PRICE_OUT = 0.75, 3.75  # USD per million tokens, gemini-3.8-flash through 2026-12-31
CALL_SIGN = re.compile(r"\b(?:[A-Z]{1,2}|[A-Z][0-9]|[0-9][A-Z])[0-9][A-Z0-9]{0,3}[A-Z](?:/[A-Z0-9]{1,3})?\b")
UNSURE = ("[...]", "unreadable", "unclear", "garble", "damaged", "corrupt", "fragment", "unknown", "uncertain",
          "noise", "stray", "(?)")


# ---------------------------------------------------------------- golden examples

def parse_example(path: pathlib.Path) -> dict:
    """Pieces and the piece-tier references of one golden example (the SRUTI-005 format)."""
    text = path.read_text(encoding="utf-8")
    pieces_md = text.split("\n## Pieces", 1)[1].split("\n## ", 1)[0]
    pieces = re.findall(r"```(?:text)?\n(.*?)\n```", pieces_md, flags=re.DOTALL)
    refs_md = text.split("\n## Reference — piece tier", 1)[1].split("\n## ", 1)[0]
    refs = []
    for block in re.split(r"\n### Piece ", refs_md)[1:]:
        head, _, body = block.partition("\n")
        action = head.split("·")[-1].strip()
        rows = [(m.group(1), m.group(2).strip())
                for m in re.finditer(r"^\| `(.+?)` \| (.+?) \|$", body, flags=re.MULTILINE)]
        msg = re.search(r"\*\*Message:\*\* (.+?)(?:\n\n|\n### |\Z)", body, flags=re.DOTALL)
        refs.append({"action": action, "gloss": rows,
                     "message": " ".join(msg.group(1).split()) if msg else ""})
    if len(refs) != len(pieces):
        raise SystemExit(f"{path.name}: {len(pieces)} pieces but {len(refs)} reference blocks")
    return {"name": path.stem, "pieces": pieces, "refs": refs}


# ---------------------------------------------------------------- checks

def schema_errors(ans) -> list[str]:
    if not isinstance(ans, dict):
        return ["the answer is not a JSON object"]
    errors = []
    gloss = ans.get("gloss")
    if not isinstance(gloss, list) or not all(
            isinstance(r, dict) and isinstance(r.get("token"), str) and isinstance(r.get("meaning"), str)
            for r in gloss):
        errors.append("gloss is not a list of {token, meaning}")
    action = ans.get("action")
    if action not in ("none", "append", "rebuild"):
        errors.append(f"action {action!r} is not none / append / rebuild")
    if action == "append" and not (isinstance(ans.get("message"), str) and ans["message"].strip()):
        errors.append("append without a message")
    if action == "rebuild" and not (isinstance(ans.get("rebuilt"), list) and ans["rebuilt"]
                                    and all(isinstance(e, str) for e in ans["rebuilt"])):
        errors.append("rebuild without a rebuilt list")
    return errors


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def uncovered_tokens(piece: str, gloss: list[dict]) -> list[str]:
    """Raw tokens that appear in no gloss token (spaces ignored, so joined or split tokens count)."""
    joined = squash(" ".join(r.get("token", "") for r in gloss))
    return [tok for tok in piece.split() if squash(tok) not in joined]


def invented_call_signs(ans: dict, raw_so_far: str) -> list[str]:
    """Call signs in the answer that the raw pieces do not contain (spaces ignored, so joined fragments
    count). A (?) does not excuse one: the prompt forbids offering a call sign that is not in the text."""
    texts = [ans.get("message") or ""] + list(ans.get("rebuilt") or [])
    texts += [r.get("meaning", "") for r in ans.get("gloss") or []]
    raw = squash(raw_so_far)
    invented = []
    for text in texts:
        for m in CALL_SIGN.finditer(text):
            if squash(m.group(0)) not in raw and m.group(0) not in invented:
                invented.append(m.group(0))
    return invented


def guessed_unreadable(ans: dict, ref: dict) -> list[str]:
    """Tokens the reference marks unreadable that the answer glosses with no sign of doubt."""
    model = {squash(r.get("token", "")): r.get("meaning", "") for r in ans.get("gloss") or []}
    guessed = []
    for token, meaning in ref["gloss"]:
        if not meaning.startswith("[...]"):
            continue
        got = model.get(squash(token))
        doubtful = got is not None and (got.lstrip().startswith("[") or "?" in got
                                        or any(word in got.lower() for word in UNSURE))
        if got is not None and not doubtful:
            guessed.append(token)
    return guessed


# ---------------------------------------------------------------- the run

def apply_action(section3: list[dict], ans: dict) -> None:
    """Section 3 as the window shows it: none bumps a repeat counter, rebuild replaces the shown window."""
    action = ans.get("action")
    if action == "none" and section3:
        section3[-1]["repeats"] += 1
    elif action == "append" and ans.get("message"):
        section3.append({"text": ans["message"], "repeats": 1, "rebuilt": False})
    elif action == "rebuild" and ans.get("rebuilt"):
        del section3[-RECENT_ENTRIES:]
        section3.extend({"text": e, "repeats": 1, "rebuilt": True} for e in ans["rebuilt"])


def run_example(example: dict, system: str, call) -> list[dict]:
    section3: list[dict] = []
    results = []
    for i, piece in enumerate(example["pieces"]):
        shown = [e["text"] for e in section3[-RECENT_ENTRIES:]]
        user = explain_piece.build_user(example["pieces"][max(0, i - CONTEXT_PIECES):i], shown, piece)
        result = {"piece": piece, "ref": example["refs"][i], "failures": [], "notes": []}
        try:
            ans, seconds, stats = call(system, user)
        except Exception as exc:  # noqa: BLE001 - a failed call is a result, not a crash
            result.update(ans=None, seconds=0.0, stats={}, failures=[f"call failed: {type(exc).__name__}: {exc}"])
            results.append(result)
            continue
        result.update(ans=ans, seconds=seconds, stats=stats)
        check(result, example, i)
        if not any(f.startswith("schema:") for f in result["failures"]):
            apply_action(section3, ans)
        result["section3"] = [dict(e) for e in section3]
        results.append(result)
    return results


def check(result: dict, example: dict, i: int) -> None:
    """The automatic checks on one answer; fills result["failures"] and result["notes"]."""
    ans, piece = result["ans"], example["pieces"][i]
    result["failures"], result["notes"] = [], []
    errors = schema_errors(ans)
    if errors:
        result["failures"] += [f"schema: {e}" for e in errors]
        return
    if result["seconds"] > BUDGET_S:
        result["failures"].append(f"over budget: {result['seconds']:.1f} s > {BUDGET_S:.0f} s")
    missing = uncovered_tokens(piece, ans["gloss"])
    if missing:
        result["failures"].append("gloss misses: " + " ".join(f"`{t}`" for t in missing))
    invented = invented_call_signs(ans, " ".join(example["pieces"][: i + 1]))
    if invented:
        result["failures"].append("call sign not in the raw text: " + ", ".join(invented))
    guessed = guessed_unreadable(ans, example["refs"][i])
    if guessed:
        result["failures"].append("unreadable text glossed as certain: " + " ".join(f"`{t}`" for t in guessed))
    if ans["action"] == "rebuild":
        result["notes"].append("rebuild")


def rescore(saved: pathlib.Path) -> pathlib.Path:
    """Re-run the checks on a saved run's answers against the current references; no model call."""
    data = json.loads(saved.read_text(encoding="utf-8"))
    runs = {}
    for name, results in data["runs"].items():
        example = parse_example(EXAMPLES / f"{name}.md")
        for i, result in enumerate(results):
            result["ref"] = example["refs"][i]
            if result["ans"] is not None:
                check(result, example, i)
        runs[name] = results
    out = saved.with_suffix(".md")
    out.write_text(report(runs, data["model"], data["glossary"]), encoding="utf-8")
    return out


def cost_usd(stats: dict) -> float:
    out = stats.get("out_tokens", 0) + stats.get("thought_tokens", 0)
    return (stats.get("prompt_tokens", 0) * PRICE_IN + out * PRICE_OUT) / 1e6


# ---------------------------------------------------------------- the report

def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def report(runs: dict, model: str, glossary: str) -> str:
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Eval — {model}, glossary {glossary}", "",
             f"**Run:** {when} · **Examples:** {', '.join(runs)} · **Budget:** {BUDGET_S:.0f} s per piece", "",
             "| Example | Pieces | Passed | Latency min / avg / max | Tokens in / out | Cost | Actions (model) |",
             "|---|---|---|---|---|---|---|"]
    for name, results in runs.items():
        secs = [r["seconds"] for r in results if r["ans"] is not None]
        tin = sum(r["stats"].get("prompt_tokens", 0) for r in results)
        tout = sum(r["stats"].get("out_tokens", 0) + r["stats"].get("thought_tokens", 0) for r in results)
        actions = [r["ans"].get("action") for r in results if isinstance(r["ans"], dict)]
        counts = ", ".join(f"{a} {actions.count(a)}" for a in ("append", "none", "rebuild") if actions.count(a))
        lat = f"{min(secs):.1f} / {sum(secs) / len(secs):.1f} / {max(secs):.1f} s" if secs else "—"
        lines.append(f"| {name} | {len(results)} | {sum(not r['failures'] for r in results)} | {lat} | "
                     f"{tin} / {tout} | ${sum(cost_usd(r['stats']) for r in results):.4f} | {counts} |")
    for name, results in runs.items():
        lines += ["", f"## {name}"]
        for n, r in enumerate(results, 1):
            ans = r["ans"] if isinstance(r["ans"], dict) else {}
            verdict = "✅ pass" if not r["failures"] else "❌ " + "; ".join(r["failures"])
            lines += ["", f"### Piece {n} — {verdict}", "",
                      f"`{cell(r['piece'].strip())}`", "",
                      f"**Action:** model `{ans.get('action', '—')}` · reference `{r['ref']['action']}` · "
                      f"{r['seconds']:.1f} s · ${cost_usd(r['stats']):.4f}"
                      + (" · " + ", ".join(r["notes"]) if r["notes"] else ""), "",
                      "| Model token | Model meaning |", "|---|---|"]
            rows = ans.get("gloss") if isinstance(ans.get("gloss"), list) else []
            lines += [f"| `{cell(str(g.get('token', '')))}` | {cell(str(g.get('meaning', '')))} |"
                      for g in rows if isinstance(g, dict)]
            if not rows and ans:
                lines.append(f"| (no valid gloss) | {cell(json.dumps(ans.get('gloss'), ensure_ascii=False))} |")
            rebuilt = ans.get("rebuilt") if isinstance(ans.get("rebuilt"), list) else []
            model_msg = ans.get("message") or ("; ".join(map(str, rebuilt)) or "—")
            lines += ["", f"**Model message:** {cell(model_msg)}", "",
                      f"**Reference message:** {cell(r['ref']['message'])}"]
        final = results[-1].get("section3") if results else None
        if final:
            lines += ["", "**Section 3 at the end:**", ""]
            lines += [f"{i}. {'⟲ ' if e['rebuilt'] else ''}{cell(e['text'])}"
                      + (f" ×{e['repeats']}" if e["repeats"] > 1 else "") for i, e in enumerate(final, 1)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- offline self-test

def selftest() -> int:
    example = {
        "name": "selftest",
        "pieces": ["CQ CQ DE DJ0YI DJ0YI K", "DJ0YI DE OK7DA/P K", "R 5NN K", "CQ DE DJ0YI K"],
        "refs": [{"action": "append", "gloss": [], "message": ""}] * 3
        + [{"action": "none", "gloss": [("XQZ", "[...] unreadable")], "message": ""}],
    }
    canned = iter([
        ({"gloss": [{"token": "CQ CQ", "meaning": "general call"}, {"token": "DE", "meaning": "from"},
                    {"token": "DJ0YI DJ0YI", "meaning": "call sign DJ0YI"}, {"token": "K", "meaning": "over"}],
          "action": "append", "message": "General call from DJ0YI. Over."}, 2.1),
        ({"gloss": [{"token": "DJ0YI DE OK7DA/P K", "meaning": "DJ0YI from OK7DA/P, over"}],
          "action": "append", "message": "OK7DA/P, also known as OK7XYZ, calls DJ0YI."}, 2.4),
        ({"gloss": "R 5NN K", "action": "append", "message": "Roger, 599."}, 1.9),
        ({"gloss": [{"token": "CQ DE DJ0YI K", "meaning": "CQ from DJ0YI, over"}],
          "action": "rebuild", "rebuilt": ["General call from DJ0YI; OK7DA/P answered."]}, 2.0),
    ])

    def fake_call(system, user):
        ans, seconds = next(canned)
        return ans, seconds, {"prompt_tokens": 1000, "out_tokens": 400, "thought_tokens": 100}

    results = run_example(example, explain_piece.build_system("hints"), fake_call)
    want = [[], ["call sign not in the raw text: OK7XYZ"], ["schema: gloss is not a list of {token, meaning}"], []]
    ok = True
    for n, (r, expected) in enumerate(zip(results, want), 1):
        good = r["failures"] == expected
        ok &= good
        print(f"{'ok ' if good else 'BAD'} piece {n}: failures {r['failures']}" + ("" if good else f" (want {expected})"))
    rebuilt = results[3]["notes"] == ["rebuild"] and results[3]["section3"][-1]["rebuilt"]
    ok &= rebuilt
    print(f"{'ok ' if rebuilt else 'BAD'} piece 4: rebuild counted and applied to section 3, not failed")
    ref = {"gloss": [("EE E", "[...] fragments")]}
    marks_ok = not guessed_unreadable({"gloss": [{"token": "EE E", "meaning": "[dits]"}]}, ref) \
        and guessed_unreadable({"gloss": [{"token": "EE E", "meaning": "the letter E"}]}, ref) == ["EE E"]
    alternatives_ok = not invented_call_signs({"message": "garbled (?) OM3CPF/OM3CNF"}, "UOM3CNF OM3CPF") \
        and invented_call_signs({"message": "UW3WU or UR3WU"}, "UW3WU") == ["UR3WU"] \
        and invented_call_signs({"message": "UW3WU (?) UR3WU (?)"}, "UW3WU") == ["UR3WU"] \
        and not invented_call_signs({"message": "IU3FEJ (?) from IZ4PHG"}, "IU3 F E JDE IZ4PHG")
    ok &= marks_ok and alternatives_ok
    print(f"{'ok ' if marks_ok else 'BAD'} a bracketed mark counts as doubt; a plain reading of an unreadable token fails")
    print(f"{'ok ' if alternatives_ok else 'BAD'} slash alternatives are two call signs; a new one fails, (?) or not;"
          " joined fragments pass")
    text = report({"selftest": results}, "canned", "hints")
    has_rows = "OK7XYZ" in text and "Reference message" in text
    ok &= has_rows
    print(f"{'ok ' if has_rows else 'BAD'} the report renders the checks and the side-by-side rows")
    return 0 if ok else 1


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", default="gemini-3.8-flash")
    ap.add_argument("--glossary", choices=["full", "hints", "none"], default="hints")
    ap.add_argument("--examples", help="comma-separated number prefixes, e.g. 001,003 (default: all)")
    ap.add_argument("--live", action="store_true", help="call the model for real (paid)")
    ap.add_argument("--selftest", action="store_true", help="offline check of the loop with canned answers")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--rescore", help="a saved run (.json under poc/eval/): re-run the checks, no model call")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.rescore:
        out = rescore(pathlib.Path(args.rescore))
        print(f"report: {out}", file=sys.stderr)
        return 0
    if not args.live:
        print("no --live: refusing to call the model (a paid call). Use --selftest for the offline check.",
              file=sys.stderr)
        return 2
    wanted = args.examples.split(",") if args.examples else None
    paths = sorted(p for p in EXAMPLES.glob("[0-9][0-9][0-9]-*.md")
                   if wanted is None or p.name[:3] in wanted)
    system = explain_piece.build_system(args.glossary)

    def live_call(system_text, user):
        return explain_piece.call(args.model, system_text, user, args.timeout)

    runs = {}
    for path in paths:
        example = parse_example(path)
        t0 = time.monotonic()
        runs[example["name"]] = run_example(example, system, live_call)
        passed = sum(not r["failures"] for r in runs[example["name"]])
        print(f"{example['name']}: {passed}/{len(example['pieces'])} pieces pass ({time.monotonic() - t0:.0f} s)",
              file=sys.stderr)
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out = REPORTS / f"{stamp}-{args.model}-{args.glossary}.md"
    out.write_text(report(runs, args.model, args.glossary), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(
        {"model": args.model, "glossary": args.glossary, "runs": runs}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"report: {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
