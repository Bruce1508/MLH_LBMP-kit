# Interfaces

These are the functions Bruce's `app.py` and `evaluate.py` call. All of them return plain dicts.

| Function | File | Returns |
| --- | --- | --- |
| `extract_findings(note_text, offline=None)` | `extract.py` | findings dict (below) |
| `combine(findings_list)` | `score.py` | one findings dict merged from several notes (sorted by date) |
| `score(findings)` | `score.py` | `{"risk", "points", "reasons", "gold_coast", "regions", "advice", "evidence"}` |
| `run_timeline(notes_dir, offline=None)` | `timeline.py` | `[{"date", "risk", "points", "file", "source", "reasons", "new_findings", "regions", "gold_coast", "findings"}]` |
| `first_flag(steps, at_least="high")` | `timeline.py` | first timeline step at that risk, or `None` |

The `offline` argument controls which extractor runs:
- `offline=None` (the default) uses Gemini if `GEMINI_API_KEY` is set and the keyword extractor otherwise.
- `offline=True` always uses the keyword extractor. Use it to build the UI without spending quota.

## Findings (one note)

In the findings, `true` means present, `false` means checked and absent, and `null` means not mentioned.

```json
{
  "date": "2024-10-14",
  "source": "GP referral",
  "weakness_regions": ["right hand"],
  "painless": true,
  "sensory_symptoms": false,
  "wasting": true,
  "fasciculations": false,
  "cramps": true,
  "brisk_reflexes": null,
  "upgoing_plantar_or_hoffmann": null,
  "normal_sensory_nerve_tests": null,
  "failed_local_treatment": false,
  "weight_loss": false,
  "speech_or_swallow_change": false,
  "breathing_change": false,
  "evidence": [{"field": "wasting", "quote": "thenar wasting noted"}]
}
```

`evidence` is an addition to the agreed schema. It holds short quotes from the note, so the app can show why each finding was set.

## Score result

```json
{
  "risk": "high",
  "points": 19,
  "reasons": [
    "Matches the Gold Coast pattern: upper + lower motor neuron signs and getting worse",
    "+3 Weakness has spread to a second region (right arm, left leg)",
    "+3 Upper and lower motor neuron signs together",
    "+2 Muscle wasting"
  ],
  "gold_coast": true,
  "regions": ["right arm", "left leg"],
  "advice": "Urgent referral to neurology ...",
  "evidence": [{"field": "wasting", "quote": "...", "date": "2024-10-14"}]
}
```

Risk is set as follows:
- `high`: at least `risk_thresholds.high` points, or the Gold Coast pattern is met. That pattern is an upper motor neuron sign plus a lower motor neuron sign, plus a sign of getting worse (spread to a second region, or no improvement after local treatment).
- `medium`: at least `risk_thresholds.medium` points.
- `low`: everything else.

All weights and wording live in `rules.json`, so Mia can edit them without touching code.

## How notes are combined

`combine()` merges a patient's notes as follows:
- A finding that is `true` in any note stays `true`, so signs add up over time.
- For `sensory_symptoms` and `painless`, the most recent note that mentions them wins. For example, early tingling put down to carpal tunnel is overridden by a later "sensation intact".
- `weakness_regions` from all notes are joined into one list.
