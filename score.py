"""Score findings against the ALS red-flag rules in rules.json.

    from score import combine, score
    combined = combine([nf1, nf2, ...], dates=["2024-03-01", ...])  # merge notes for one patient
    result = score(combined)          # or score(nf) for a single note

result = {
    "score": 14, "level": "urgent" | "monitor" | "low",
    "gold_coast": True, "recommendation": "...",
    "reasons": [{"rule": "Muscle wasting", "points": 2, "evidence": [{"date": "...", "quote": "..."}]}, ...],
    "regions": ["cervical", "lumbosacral"],
}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from schema import FEATURES, NoteFindings, Region, Status

RULES_PATH = Path(__file__).parent / "rules.json"

# For these, the most recent explicit mention wins (an old "numbness" note
# should not outweigh a later documented normal sensory exam). For every other
# feature, "present" in any note wins: signs accumulate.
LATEST_WINS = {"sensory_normal", "sensory_loss", "significant_pain"}

_REGION_ORDER = [r.value for r in Region]


def load_rules(path: Path | str = RULES_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def combine(notes: Iterable[NoteFindings], dates: Optional[Iterable[Optional[str]]] = None) -> dict:
    """Merge findings from several notes (oldest first) into one dict:
    {feature: {"status", "regions", "evidence": [{"date", "quote"}], "first_seen"}}
    """
    notes = list(notes)
    dates = list(dates) if dates is not None else [n.note_date for n in notes]
    out: dict[str, dict] = {
        f: {"status": Status.not_mentioned.value, "regions": [], "evidence": [], "first_seen": None}
        for f in FEATURES
    }
    for nf, date in zip(notes, dates):
        date = date or nf.note_date
        for feat in FEATURES:
            f = getattr(nf.findings, feat)
            if f.status == Status.not_mentioned:
                continue
            cur = out[feat]
            if feat in LATEST_WINS:
                if f.status.value != cur["status"]:
                    cur["evidence"] = []
                cur["status"] = f.status.value
            elif f.status == Status.present:
                cur["status"] = Status.present.value
            elif cur["status"] == Status.not_mentioned.value:
                cur["status"] = Status.absent.value

            if cur["status"] == f.status.value:
                if f.status == Status.present and cur["first_seen"] is None:
                    cur["first_seen"] = date
                cur["regions"] = sorted(set(cur["regions"]) | {r.value for r in f.regions}, key=_REGION_ORDER.index)
                if f.evidence:
                    cur["evidence"].append({"date": date, "quote": f.evidence})
    return out


def _is_combined(x) -> bool:
    return isinstance(x, dict) and all(f in x for f in FEATURES)


def score(findings, rules: Optional[dict] = None) -> dict:
    """findings: a combine() result, a NoteFindings, or a list of NoteFindings."""
    rules = rules or load_rules()
    if isinstance(findings, NoteFindings):
        findings = combine([findings])
    elif not _is_combined(findings):
        findings = combine(findings)

    present = {f for f, v in findings.items() if v["status"] == Status.present.value}
    reasons: list[dict] = []
    total = 0

    for feat, rule in rules["feature_points"].items():
        if feat in present and rule["points"] != 0:
            total += rule["points"]
            reasons.append({"rule": rule["why"], "feature": feat, "points": rule["points"],
                            "evidence": findings[feat]["evidence"]})

    def regions_of(feats: list[str]) -> set[str]:
        return {r for f in feats if f in present for r in findings[f]["regions"]}

    lmn_present = any(f in present for f in rules["lmn_features"])
    umn_present = any(f in present for f in rules["umn_features"])
    lmn_regions = regions_of(rules["lmn_features"])
    umn_regions = regions_of(rules["umn_features"])
    motor_regions = regions_of(rules["motor_features"])
    if "bulbar_symptoms" in present:
        motor_regions.add(Region.bulbar.value)

    pp = rules["pattern_points"]
    # Same region when the notes say where; if the UMN sign has no region, count it anyway.
    umn_lmn = lmn_present and umn_present and (not umn_regions or not lmn_regions or bool(umn_regions & lmn_regions))
    lmn_two = len(lmn_regions) >= 2
    spread = len(motor_regions) >= 2
    for key, hit, feats in (("umn_and_lmn", umn_lmn, rules["umn_features"] + rules["lmn_features"]),
                            ("lmn_two_regions", lmn_two, rules["lmn_features"]),
                            ("motor_spread", spread, rules["motor_features"])):
        if hit:
            total += pp[key]["points"]
            ev = [e for f in feats if f in present for e in findings[f]["evidence"]][:4]
            reasons.append({"rule": pp[key]["why"], "feature": key, "points": pp[key]["points"], "evidence": ev})

    # Spread to a new region counts as documented progression.
    progressive = "progression" in present or "treatment_failure" in present or spread
    gold_coast = progressive and (umn_lmn or lmn_two) and "conduction_block" not in present

    th = rules["thresholds"]
    if gold_coast or total >= th["urgent"]:
        level = "urgent"
    elif total >= th["monitor"]:
        level = "monitor"
    else:
        level = "low"

    reasons.sort(key=lambda r: -r["points"])
    return {
        "score": total,
        "level": level,
        "gold_coast": gold_coast,
        "recommendation": rules["recommendations"][level],
        "reasons": reasons,
        "regions": sorted(motor_regions, key=_REGION_ORDER.index),
    }


if __name__ == "__main__":
    import sys
    from extract import extract

    if len(sys.argv) < 2:
        sys.exit("usage: python score.py NOTE.txt [NOTE2.txt ...] [--offline]")
    offline = True if "--offline" in sys.argv else None
    paths = [Path(p) for p in sys.argv[1:] if not p.startswith("--")]
    nfs = [extract(p.read_text(encoding="utf-8"), offline=offline) for p in paths]
    print(json.dumps(score(combine(nfs)), indent=2))
