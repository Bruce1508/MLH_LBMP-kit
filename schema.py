"""Findings schema shared by extract.py, score.py, timeline.py and app.py.

One clinical note -> one NoteFindings. Every red-flag feature has the same shape:
    status:   "present" | "absent" | "not_mentioned"
    regions:  body regions it involves (bulbar, cervical, thoracic, lumbosacral)
    evidence: a short quote from the note that supports the status
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Status(str, Enum):
    present = "present"
    absent = "absent"
    not_mentioned = "not_mentioned"


class Region(str, Enum):
    bulbar = "bulbar"            # speech, swallowing, tongue, face
    cervical = "cervical"        # neck, arms, hands
    thoracic = "thoracic"        # trunk, chest wall, breathing muscles
    lumbosacral = "lumbosacral"  # legs, feet


class NoteType(str, Enum):
    gp = "gp"
    referral = "referral"
    consult = "consult"
    physio = "physio"
    emg = "emg"
    imaging = "imaging"
    surgery = "surgery"
    other = "other"


class Finding(BaseModel):
    status: Status = Status.not_mentioned
    regions: list[Region] = Field(default_factory=list)
    evidence: str = ""


# Feature name -> what it means. The prompt in extract.py is built from this,
# so add or rename features here only.
FEATURES: dict[str, str] = {
    "painless_weakness": "Muscle weakness that is NOT explained by pain (painless, or pain is minor).",
    "muscle_atrophy": "Muscle wasting / atrophy (e.g. thenar or first dorsal interosseous wasting, thin calves).",
    "fasciculations": "Fasciculations / muscle twitching seen or reported.",
    "cramps": "Muscle cramps.",
    "umn_signs": "Upper motor neuron signs: brisk/hyperactive reflexes, Hoffmann, Babinski/up-going plantar, clonus, spasticity.",
    "reduced_reflexes": "Reduced or absent reflexes in a weak limb.",
    "sensory_normal": "Sensation documented as normal/intact in the affected area.",
    "sensory_loss": "Objective sensory loss, numbness, or abnormal sensory nerve conduction.",
    "significant_pain": "Pain is a major feature of the presentation.",
    "bulbar_symptoms": "Slurred speech (dysarthria), swallowing difficulty (dysphagia), tongue wasting or tongue fasciculations.",
    "respiratory_symptoms": "Shortness of breath, orthopnea, reduced FVC, morning headaches from hypoventilation.",
    "weight_loss": "Unintentional weight loss.",
    "progression": "Symptoms are getting worse over time.",
    "treatment_failure": "No improvement after treatment (e.g. carpal tunnel release, physio, steroid injection, surgery).",
    "emg_denervation": "EMG shows active and/or chronic denervation, especially in more than one region.",
    "conduction_block": "Nerve conduction shows motor conduction block (points toward MMN, an ALS mimic).",
}


class Findings(BaseModel):
    painless_weakness: Finding = Field(default_factory=Finding)
    muscle_atrophy: Finding = Field(default_factory=Finding)
    fasciculations: Finding = Field(default_factory=Finding)
    cramps: Finding = Field(default_factory=Finding)
    umn_signs: Finding = Field(default_factory=Finding)
    reduced_reflexes: Finding = Field(default_factory=Finding)
    sensory_normal: Finding = Field(default_factory=Finding)
    sensory_loss: Finding = Field(default_factory=Finding)
    significant_pain: Finding = Field(default_factory=Finding)
    bulbar_symptoms: Finding = Field(default_factory=Finding)
    respiratory_symptoms: Finding = Field(default_factory=Finding)
    weight_loss: Finding = Field(default_factory=Finding)
    progression: Finding = Field(default_factory=Finding)
    treatment_failure: Finding = Field(default_factory=Finding)
    emg_denervation: Finding = Field(default_factory=Finding)
    conduction_block: Finding = Field(default_factory=Finding)


class NoteFindings(BaseModel):
    """What extract() returns for one note."""
    note_date: Optional[str] = Field(None, description="YYYY-MM-DD if the note states a date")
    note_type: NoteType = NoteType.other
    author_role: str = Field("", description="e.g. family doctor, physiotherapist, neurologist")
    summary: str = Field("", description="One-sentence plain summary of the note")
    other_diagnosis_considered: str = Field("", description="Diagnosis the author proposes, if any")
    findings: Findings = Field(default_factory=Findings)


assert set(FEATURES) == set(Findings.model_fields), "FEATURES and Findings must list the same features"
