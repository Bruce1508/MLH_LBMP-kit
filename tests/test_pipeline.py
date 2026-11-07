"""Offline tests: no API key needed.  Run: python -m pytest -q"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extract import extract_offline  # noqa: E402
from schema import Status  # noqa: E402
from score import combine, score  # noqa: E402
from timeline import run_timeline  # noqa: E402


def test_negation():
    nf = extract_offline("No fasciculations. Sensation intact. Denies numbness.")
    f = nf.findings
    assert f.fasciculations.status == Status.absent
    assert f.sensory_normal.status == Status.present
    assert f.sensory_loss.status == Status.absent


def test_carpal_tunnel_mimic_is_low():
    note = ("Numbness and tingling in the right thumb and index finger, worse at night, painful wrist. "
            "Positive Phalen's test. Reduced sensation in median distribution. Reflexes normal.")
    assert score(extract_offline(note))["level"] == "low"


def test_mmn_conduction_block_not_gold_coast():
    note = ("Painless weakness of the left hand and right forearm with wasting and fasciculations. "
            "Sensation intact. Nerve conduction shows motor conduction block in the left ulnar nerve.")
    assert score(extract_offline(note))["gold_coast"] is False


def test_classic_als_note_is_urgent():
    note = ("Progressive painless weakness of the right hand, now also tripping on the left foot. "
            "Wasting of right thenar muscles. Fasciculations in right arm and left calf. "
            "Brisk reflexes and positive Hoffmann sign. Sensation normal.")
    r = score(extract_offline(note))
    assert r["level"] == "urgent" and r["gold_coast"]


def test_combine_keeps_earliest_and_latest_sensory():
    a = extract_offline("Tingling in the fingers at night.")
    b = extract_offline("Sensation intact.")
    c = combine([a, b], ["2024-01-01", "2024-06-01"])
    assert c["sensory_loss"]["status"] == "absent"
    assert c["sensory_normal"]["status"] == "present"


def test_sample_timeline_flags_before_neurology():
    tl = run_timeline(ROOT / "data" / "sample", offline=True, diagnosis_date="2025-03-18")
    assert tl["first_urgent"] is not None
    assert tl["first_urgent"]["date"] < "2025-03-18"
