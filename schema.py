"""Findings schema shared by extract.py, score.py, timeline.py and app.py.

One note -> one findings dict:
    true  = the note says it is present
    false = the note says it was checked and is absent
    null  = the note does not mention it

Example:
{
  "date": "2024-10-14", "source": "GP referral",
  "weakness_regions": ["right hand"],
  "painless": true, "sensory_symptoms": false, "wasting": true, "fasciculations": false,
  "cramps": true, "brisk_reflexes": null, "upgoing_plantar_or_hoffmann": null,
  "normal_sensory_nerve_tests": null, "failed_local_treatment": false, "weight_loss": false,
  "speech_or_swallow_change": false, "breathing_change": false,
  "evidence": [{"field": "wasting", "quote": "thenar wasting noted"}]
}
"evidence" is extra (not in the original spec): short quotes so the app can show WHY.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# Yes/no findings, with a plain-English meaning. The Gemini prompt is built from this.
FLAGS: dict[str, str] = {
    "painless": "The weakness is painless (no significant pain with it).",
    "sensory_symptoms": "Numbness, tingling, pins and needles, or reduced sensation. (ALS usually has NONE.)",
    "wasting": "Muscle wasting / atrophy: muscles visibly thinner, e.g. at the base of the thumb.",
    "fasciculations": "Fasciculations: small visible muscle twitches under the skin.",
    "cramps": "Muscle cramps.",
    "brisk_reflexes": "Brisk / hyperactive / increased reflexes, or clonus or spasticity.",
    "upgoing_plantar_or_hoffmann": "Up-going plantar (positive Babinski) or positive Hoffmann sign.",
    "normal_sensory_nerve_tests": "Nerve conduction study shows NORMAL sensory nerves.",
    "failed_local_treatment": "No improvement after a local treatment, e.g. carpal tunnel surgery, splint, physio, injection.",
    "weight_loss": "Unintentional weight loss.",
    "speech_or_swallow_change": "Slurred speech, swallowing trouble, choking, or tongue wasting/twitching.",
    "breathing_change": "Shortness of breath, breathless lying flat, or reduced breathing test (FVC).",
}

FIELDS = ["date", "source", "weakness_regions", *FLAGS]


class Evidence(BaseModel):
    field: str = Field(description="One of the finding names")
    quote: str = Field(description="Short exact quote from the note")


class Findings(BaseModel):
    date: Optional[str] = Field(None, description="Date of the note as YYYY-MM-DD, or null")
    source: Optional[str] = Field(None, description="Who wrote it, e.g. 'GP referral', 'physio', 'neurology consult'")
    weakness_regions: list[str] = Field(default_factory=list,
                                        description="Where there is weakness, e.g. 'right hand', 'left foot', 'speech'")
    painless: Optional[bool] = None
    sensory_symptoms: Optional[bool] = None
    wasting: Optional[bool] = None
    fasciculations: Optional[bool] = None
    cramps: Optional[bool] = None
    brisk_reflexes: Optional[bool] = None
    upgoing_plantar_or_hoffmann: Optional[bool] = None
    normal_sensory_nerve_tests: Optional[bool] = None
    failed_local_treatment: Optional[bool] = None
    weight_loss: Optional[bool] = None
    speech_or_swallow_change: Optional[bool] = None
    breathing_change: Optional[bool] = None
    evidence: list[Evidence] = Field(default_factory=list)


def empty_findings() -> dict:
    return Findings().model_dump()


assert set(FLAGS) | {"date", "source", "weakness_regions", "evidence"} == set(Findings.model_fields)
