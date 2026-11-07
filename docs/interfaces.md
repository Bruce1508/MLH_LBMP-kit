# Interfaces (agree at the 1:30 PM schema meeting)

Once these are agreed, Peter's pipeline and Bruce's app can be built in parallel.

## Functions Bruce calls

| Function | File | Input | Returns |
| --- | --- | --- | --- |
| `extract(text, offline=None)` | `extract.py` | note text | `NoteFindings` (pydantic; `.model_dump(mode="json")` for a dict) |
| `combine(notes, dates=None)` | `score.py` | list of `NoteFindings`, oldest first | merged dict, one entry per feature |
| `score(findings)` | `score.py` | a `NoteFindings`, a list of them, or a `combine()` result | result dict (below) |
| `run_timeline(folder, offline=None, diagnosis_date=None)` | `timeline.py` | folder of dated `.txt` notes | `{"steps", "first_urgent", "first_monitor", "final", "months_earlier"?}` |

`offline=None` means Gemini is used when `GEMINI_API_KEY` is set and the keyword extractor otherwise. Pass `offline=True` to build the UI without spending quota.

## Findings JSON (one note)

```json
{
  "note_date": "2024-12-03",
  "note_type": "gp",
  "author_role": "family doctor",
  "summary": "Hand weakness worse despite surgery; new left foot tripping.",
  "other_diagnosis_considered": "carpal tunnel syndrome",
  "findings": {
    "muscle_atrophy": {"status": "present", "regions": ["cervical"], "evidence": "wasting of right thenar"},
    "sensory_loss":   {"status": "absent",  "regions": [], "evidence": "Denies numbness."},
    "...": "16 features in total, listed in schema.FEATURES"
  }
}
```

- `status`: `present` · `absent` · `not_mentioned`
- `regions`: `bulbar` · `cervical` · `thoracic` · `lumbosacral`

## Score result

```json
{
  "score": 19,
  "level": "urgent",
  "gold_coast": true,
  "recommendation": "Urgent referral to neurology ...",
  "regions": ["cervical", "lumbosacral"],
  "reasons": [
    {"rule": "Muscle wasting", "feature": "muscle_atrophy", "points": 2,
     "evidence": [{"date": "2024-12-03", "quote": "wasting of right thenar"}]}
  ]
}
```

`level` is `urgent` when the Gold Coast pattern is met or the score is at least `thresholds.urgent`, and `monitor` at `thresholds.monitor` or above. Everything else is `low`.

## Data folders

- `data/alex/` holds Alex's notes (typed by Mia), one `.txt` per document, named `YYYY-MM-DD_<type>.txt`.
- `data/sample/` holds an invented patient for testing the pipeline.
- `rules.json` holds the weights, thresholds and wording. Mia edits it; no code changes are needed.
