"""Run a patient's notes in date order and find the first date the tool flags them.

Notes: one .txt per document in a folder, named YYYY-MM-DD_source.txt
(a date inside the note works too if the filename has none).

    from timeline import run_timeline, first_flag
    steps = run_timeline("data/alex")
    # [{"date", "risk", "points", "file", "source", "reasons", "new_findings", "regions"}, ...]
    # each step = the score after reading notes 1..i together (combine)
    first_flag(steps)            # first step with risk "high", or None
    first_flag(steps, "medium")  # first step with risk "medium" or "high"

CLI:  python timeline.py data/alex [--offline] [--diagnosis=2026-07-15]
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from extract import extract_findings
from schema import FLAGS
from score import combine, load_rules, score

_DATE = re.compile(r"(20\d\d)[-_.](\d\d)[-_.](\d\d)")
_ORDER = {"low": 0, "medium": 1, "high": 2}


def _date_of(path: Path, text: str) -> Optional[str]:
    m = _DATE.search(path.stem) or _DATE.search(text)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def load_notes(notes_dir: str | Path) -> list[dict]:
    """[{"file", "date", "text"}] oldest first (undated last)."""
    notes = []
    for p in Path(notes_dir).glob("*.txt"):
        text = p.read_text(encoding="utf-8")
        notes.append({"file": p.name, "date": _date_of(p, text), "text": text})
    notes.sort(key=lambda n: (n["date"] is None, n["date"] or "", n["file"]))
    return notes


def run_timeline(notes_dir: str | Path, offline: Optional[bool] = None) -> list[dict]:
    rules = load_rules()
    so_far: list[dict] = []
    steps = []
    for n in load_notes(notes_dir):
        f = extract_findings(n["text"], offline=offline)
        f["date"] = n["date"] or f.get("date")   # filename date is the source of truth
        before = combine(so_far) if so_far else None
        so_far.append(f)
        merged = combine(so_far)
        result = score(merged, rules)
        new = [k for k in FLAGS if merged[k] is True and (before is None or before[k] is not True)]
        if before is not None:
            new += [f"weakness: {r}" for r in merged["weakness_regions"] if r not in before["weakness_regions"]]
        else:
            new += [f"weakness: {r}" for r in merged["weakness_regions"]]
        steps.append({
            "date": f["date"],
            "risk": result["risk"],
            "points": result["points"],
            "file": n["file"],
            "source": f.get("source"),
            "reasons": result["reasons"],
            "regions": result["regions"],
            "gold_coast": result["gold_coast"],
            "new_findings": new,
            "findings": f,
        })
    return steps


def first_flag(steps: list[dict], at_least: str = "high") -> Optional[dict]:
    return next((s for s in steps if _ORDER[s["risk"]] >= _ORDER[at_least]), None)


def months_between(d0: str, d1: str) -> float:
    return round((date.fromisoformat(d1) - date.fromisoformat(d0)).days / 30.44, 1)


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python timeline.py NOTES_DIR [--offline] [--diagnosis=YYYY-MM-DD]")
    diag = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--diagnosis=")), None)
    steps = run_timeline(args[0], offline=True if "--offline" in sys.argv else None)
    flag = first_flag(steps)

    print(f"{'date':<12}{'points':>6}  {'risk':<7} file / new findings")
    for s in steps:
        mark = "   <== FIRST HIGH-RISK FLAG" if s is flag else ""
        print(f"{s['date'] or '?':<12}{s['points']:>6}  {s['risk']:<7} {s['file']}{mark}")
        if s["new_findings"]:
            print(f"{'':<27}+ {', '.join(s['new_findings'])}")
    if flag:
        print(f"\nFirst flagged high risk: {flag['date']} ({flag['file']})")
        if diag and flag["date"]:
            print(f"That is {months_between(flag['date'], diag)} months before diagnosis ({diag}).")
    else:
        print("\nNever reached high risk.")
