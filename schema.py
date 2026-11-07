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
    "painless": "The weakness is described without pain (\"no pain\" with weakness -> true).",
    "sensory_symptoms": "Numbness, tingling, pins and needles, or sensory loss reported or found. (ALS usually has NONE.)",
    "wasting": "Muscle wasting / atrophy / flattening (e.g. flatter thenar eminence) / limb circumference loss.",
    "fasciculations": "Fasciculations: visible twitching or rippling under the skin.",
    "cramps": "Muscle cramps.",
    "brisk_reflexes": "Brisk, increased or hyperactive reflexes, or clonus or spasticity.",
    "upgoing_plantar_or_hoffmann": "Extensor (up-going) plantar response / positive Babinski, or positive Hoffmann sign.",
    "normal_sensory_nerve_tests": "Nerve conduction / sensory nerve studies reported as NORMAL.",
    "failed_local_treatment": "A treatment aimed at a local cause (carpal tunnel surgery, splint, brace, physio, injection) did not help.",
    "weight_loss": "Unintentional weight loss.",
    "speech_or_swallow_change": "Slurred or changed speech, voice change, coughing or choking when swallowing, tongue wasting/twitching.",
    "breathing_change": "Shortness of breath, especially lying flat, or reduced vital capacity (FVC).",
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
