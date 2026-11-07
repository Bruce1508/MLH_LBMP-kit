"""Turn one clinical note into structured red-flag findings (schema.NoteFindings).

    from extract import extract
    nf = extract(note_text)              # Gemini if GEMINI_API_KEY is set, else offline keywords
    nf = extract(note_text, offline=True)

Gemini results are cached in .cache/ by note text + model, so re-running the
timeline or the evaluation does not spend quota twice.

CLI:  python extract.py data/alex/2024-12-03_physio.txt [--offline]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from schema import FEATURES, Finding, Findings, NoteFindings, Region, Status

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CACHE_DIR = Path(__file__).parent / ".cache" / "extract"
MIN_SECONDS_BETWEEN_CALLS = float(os.getenv("GEMINI_MIN_INTERVAL", "0"))
_last_call = 0.0


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def has_gemini() -> bool:
    return _api_key() is not None


PROMPT = """You are helping a family doctor spot early ALS (amyotrophic lateral sclerosis).
Read the clinical note below and record what it says about each feature.

Rules:
- "present": the note says the feature is there. "absent": the note explicitly says it is not there
  (e.g. "sensation intact" makes sensory_loss absent and sensory_normal present).
  "not_mentioned": the note does not say. Never guess; only use what is written.
- regions: which body regions the feature involves:
  bulbar (speech, swallowing, tongue, face), cervical (neck, shoulders, arms, hands),
  thoracic (trunk, chest wall, breathing), lumbosacral (hips, legs, feet).
- evidence: copy a short exact quote (under 25 words) from the note. Empty if not_mentioned.
- note_date: the date of the note as YYYY-MM-DD if stated, else null.

Features:
{features}

Clinical note:
\"\"\"
{note}
\"\"\"
"""


def _prompt(note: str) -> str:
    feats = "\n".join(f"- {k}: {v}" for k, v in FEATURES.items())
    return PROMPT.format(features=feats, note=note.strip())


def _cache_path(note: str) -> Path:
    h = hashlib.sha256(f"{MODEL}\n{_prompt(note)}".encode()).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def extract_gemini(note: str, retries: int = 4) -> NoteFindings:
    global _last_call
    cache = _cache_path(note)
    if cache.exists():
        return NoteFindings.model_validate_json(cache.read_text(encoding="utf-8"))

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_api_key())
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=NoteFindings,
        temperature=0,
    )
    delay = 8.0
    for attempt in range(retries + 1):
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            _last_call = time.time()
            resp = client.models.generate_content(model=MODEL, contents=_prompt(note), config=config)
            nf = resp.parsed if isinstance(resp.parsed, NoteFindings) else NoteFindings.model_validate_json(resp.text)
            break
        except Exception as e:  # rate limit / transient server error -> back off and retry
            msg = str(e)
            transient = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "503", "500", "UNAVAILABLE", "deadline"))
            if attempt == retries or not transient:
                raise
            print(f"[extract] Gemini error ({msg[:80]}...), retrying in {delay:.0f}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(nf.model_dump_json(indent=2), encoding="utf-8")
    return nf


# ---------------------------------------------------------------------------
# Offline keyword extractor: rough, but needs no API key. Used for UI work,
# tests, and as a fallback when Gemini quota runs out.
# ---------------------------------------------------------------------------

_KEYWORDS: dict[str, list[str]] = {
    "painless_weakness": [r"painless weakness", r"weak(ness)?\b(?![^.]*\bdue to pain)", r"difficulty (gripping|buttoning|opening jars|lifting)", r"drop(ping)? (things|objects|cups)", r"foot drop", r"tripping"],
    "muscle_atrophy": [r"wast(ing|ed)", r"atroph", r"thin(ning)? (of )?(the )?(muscle|hand|calf|calves|thenar)"],
    "fasciculations": [r"fascicul", r"twitch"],
    "cramps": [r"cramp"],
    "umn_signs": [r"brisk", r"hyperreflex", r"hoffmann'?s? (sign )?(is )?(positive|present)|positive hoffmann", r"babinski", r"(up-?going|extensor) plantar", r"clonus", r"spastic"],
    "reduced_reflexes": [r"(reduced|absent|diminished|depressed) (\w+ )?reflex", r"areflexi", r"hyporeflex"],
    "sensory_normal": [r"sensation (is |was )?(intact|normal|preserved)", r"(normal|intact) sensation", r"sensory (exam(ination)? )?(is |was )?normal", r"no (numbness|sensory (loss|change|symptoms))", r"denies numbness", r"sensory (nerve )?conduction(s)? (is |are |were )?normal", r"normal sensory"],
    "sensory_loss": [r"numbness", r"tingling", r"paraesthes|paresthes", r"(reduced|decreased|diminished|loss of) sensation", r"sensory loss"],
    "significant_pain": [r"(severe|significant|constant) pain", r"painful", r"pain (is|was) (the )?(main|predominant)"],
    "bulbar_symptoms": [r"slurr", r"dysarthri", r"dysphagi", r"(difficulty|trouble) swallowing", r"chok(e|ing)", r"tongue (wasting|fascicul|atroph)", r"nasal speech"],
    "respiratory_symptoms": [r"short(ness)? of breath", r"dyspn", r"orthopn", r"\bfvc\b", r"breathless"],
    "weight_loss": [r"weight loss", r"lost \d+ ?(kg|lb|pounds)"],
    "progression": [r"progress", r"worsen", r"\b(is |are |getting |now )worse\b", r"spread", r"now (also )?(affect|involv)", r"gradually"],
    "treatment_failure": [r"no (improvement|benefit|change) (after|following|with|from|since)", r"did(n't| not) (help|improve)", r"despite (surgery|release|physio|treatment|injection)", r"not improved", r"unchanged (after|since|following)", r"failed to (help|improve)"],
    "emg_denervation": [r"denervation", r"fibrillation", r"positive sharp waves", r"(chronic )?reinnervation", r"giant motor unit"],
    "conduction_block": [r"conduction block"],
}

_REGION_WORDS: dict[Region, list[str]] = {
    Region.bulbar: [r"tongue", r"speech", r"swallow", r"slurr", r"bulbar", r"jaw", r"face|facial", r"dysarthri", r"dysphagi"],
    Region.cervical: [r"hand", r"arm", r"finger", r"thumb", r"wrist", r"shoulder", r"forearm", r"thenar", r"interosse", r"grip", r"biceps", r"triceps", r"deltoid", r"upper limb", r"cervical", r"neck"],
    Region.thoracic: [r"thoracic", r"trunk", r"abdominal", r"paraspinal", r"chest wall", r"breath", r"respirat"],
    Region.lumbosacral: [r"leg", r"foot|feet", r"ankle", r"knee", r"calf|calves", r"thigh", r"hip", r"toe", r"lower limb", r"lumbar", r"tibialis", r"quadricep", r"tripping", r"gait"],
}

_NEGATION = re.compile(r"\b(no|not|denies|denied|without|absent|negative for|nil|never|free of)\b[^.;]{0,40}$")
_SENTENCE = re.compile(r"[^.;\n]+[.;\n]?")


def _regions(text: str) -> list[Region]:
    t = text.lower()
    return [r for r, words in _REGION_WORDS.items() if any(re.search(w, t) for w in words)]


def extract_offline(note: str) -> NoteFindings:
    findings: dict[str, Finding] = {}
    sentences = [s.strip() for s in _SENTENCE.findall(note) if s.strip()]
    for feat, patterns in _KEYWORDS.items():
        best: Finding | None = None
        for sent in sentences:
            low = sent.lower()
            for pat in patterns:
                m = re.search(pat, low)
                if not m:
                    continue
                negated = bool(_NEGATION.search(low[: m.start()]))
                status = Status.absent if negated else Status.present
                f = Finding(status=status, regions=_regions(sent), evidence=sent[:200])
                if best is None or (best.status == Status.absent and status == Status.present):
                    best = f
                elif status == Status.present and best.status == Status.present:
                    best.regions = sorted(set(best.regions) | set(f.regions), key=list(Region).index)
                break
        findings[feat] = best or Finding()

    # "sensation intact" also means no sensory loss, and vice versa
    if findings["sensory_normal"].status == Status.present and findings["sensory_loss"].status == Status.not_mentioned:
        findings["sensory_loss"] = Finding(status=Status.absent, evidence=findings["sensory_normal"].evidence)
    if findings["sensory_loss"].status == Status.absent and findings["sensory_normal"].status == Status.not_mentioned:
        findings["sensory_normal"] = Finding(status=Status.present, evidence=findings["sensory_loss"].evidence)
    # weakness with major pain is not painless weakness
    if findings["painless_weakness"].status == Status.present and findings["significant_pain"].status == Status.present:
        findings["painless_weakness"].status = Status.absent

    date = re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", note)
    return NoteFindings(
        note_date=date.group(0) if date else None,
        summary="(offline keyword extraction)",
        findings=Findings(**findings),
    )


def extract(note: str, offline: bool | None = None) -> NoteFindings:
    """Main entry point. offline=None means: use Gemini if a key is set."""
    if offline is None:
        offline = not has_gemini()
    return extract_offline(note) if offline else extract_gemini(note)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python extract.py NOTE.txt [--offline]")
    text = Path(args[0]).read_text(encoding="utf-8")
    nf = extract(text, offline=True if "--offline" in sys.argv else None)
    print(nf.model_dump_json(indent=2))
