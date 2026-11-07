"""Run a patient's notes in date order and find the first date the tool flags them.

Notes live in one folder, one .txt per document, named by date:
    data/alex/2024-03-12_gp.txt
    data/alex/2024-06-02_physio.txt
(a date inside the note text also works if the filename has none)

    from timeline import run_timeline
    tl = run_timeline("data/alex")
    tl["first_urgent"]   -> {"date": "2024-12-03", "file": ..., "score": 12, ...} or None
    tl["steps"]          -> one row per note: score/level after reading notes 1..i

CLI:  python timeline.py data/alex [--offline]
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from extract import extract
from schema import NoteFindings, Status
from score import combine, load_rules, score

_DATE = re.compile(r"(20\d\d)[-_.](\d\d)[-_.](\d\d)")


def _date_of(path: Path, text: str) -> Optional[str]:
    m = _DATE.search(path.stem) or _DATE.search(text)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def load_notes(folder: str | Path) -> list[dict]:
    """[{"file", "date", "text"}] sorted oldest first (undated notes last)."""
    notes = []
    for p in Path(folder).glob("*.txt"):
        text = p.read_text(encoding="utf-8")
        notes.append({"file": p.name, "date": _date_of(p, text), "text": text})
    notes.sort(key=lambda n: (n["date"] is None, n["date"] or "", n["file"]))
    return notes


def _present(nf: NoteFindings) -> set[str]:
    return {k for k, v in nf.findings.model_dump().items() if v["status"] == Status.present.value}


def run_timeline(folder: str | Path, offline: Optional[bool] = None,
                 diagnosis_date: Optional[str] = None, rules: Optional[dict] = None) -> dict:
    rules = rules or load_rules()
    notes = load_notes(folder)
    extracted: list[NoteFindings] = []
    steps = []
    seen: set[str] = set()
    for n in notes:
        nf = extract(n["text"], offline=offline)
        extracted.append(nf)
        dates = [x["date"] for x in notes[: len(extracted)]]
        result = score(combine(extracted, dates), rules)
        new = sorted(_present(nf) - seen)
        seen |= _present(nf)
        steps.append({
            "date": n["date"],
            "file": n["file"],
            "note_type": nf.note_type.value,
            "author_role": nf.author_role,
            "summary": nf.summary,
            "other_diagnosis_considered": nf.other_diagnosis_considered,
            "new_findings": new,
            "score": result["score"],
            "level": result["level"],
            "gold_coast": result["gold_coast"],
            "result": result,
            "findings": nf.model_dump(mode="json"),
        })

    first_urgent = next((s for s in steps if s["level"] == "urgent"), None)
    first_monitor = next((s for s in steps if s["level"] in ("monitor", "urgent")), None)
    out = {
        "steps": steps,
        "first_urgent": first_urgent,
        "first_monitor": first_monitor,
        "final": steps[-1]["result"] if steps else None,
    }
    if diagnosis_date and first_urgent and first_urgent["date"]:
        d0 = date.fromisoformat(first_urgent["date"])
        d1 = date.fromisoformat(diagnosis_date)
        out["months_earlier"] = round((d1 - d0).days / 30.44, 1)
    return out


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python timeline.py FOLDER [--offline] [--diagnosis=YYYY-MM-DD]")
    diag = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--diagnosis=")), None)
    tl = run_timeline(args[0], offline=True if "--offline" in sys.argv else None, diagnosis_date=diag)

    print(f"{'date':<12}{'score':>6}  {'level':<8} file / new findings")
    for s in tl["steps"]:
        mark = " <== FIRST URGENT FLAG" if s is tl["first_urgent"] else ""
        print(f"{s['date'] or '?':<12}{s['score']:>6}  {s['level']:<8} {s['file']}{mark}")
        if s["new_findings"]:
            print(f"{'':<28}+ {', '.join(s['new_findings'])}")
    if tl["first_urgent"]:
        print(f"\nFirst urgent flag: {tl['first_urgent']['date']} ({tl['first_urgent']['file']})")
        if "months_earlier" in tl:
            print(f"That is {tl['months_earlier']} months before the diagnosis on {diag}.")
    else:
        print("\nNever reached 'urgent'.")
