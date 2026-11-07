# ALS RedFlag

Alex Chen waited two years for an ALS diagnosis. Four clinicians each saw part of the pattern, and he had a carpal tunnel operation that did nothing, but no one put it together.

ALS RedFlag reads referral letters, consult notes and physio summaries. It pulls out the key findings with Gemini and checks them against the ALS red-flag pattern: painless weakness, muscle wasting, twitching, brisk reflexes, normal sensation, spread to another limb, and no response to treatment. When the pattern appears, it recommends an urgent neurology referral and explains why.

Run on Alex's own notes in order, it would have flagged him in December 2024, about 19 months before his diagnosis.

**This tool supports clinical decisions. It does not diagnose.**

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste your Gemini API key into .env

python timeline.py data/sample --offline --diagnosis=2025-03-18   # no key needed
python timeline.py data/alex                                      # uses Gemini
python score.py data/sample/2024-12-03_gp.txt                     # score one note
python -m pytest -q
```

| File | What it does |
| --- | --- |
| `schema.py` | The findings format: 16 red-flag features, each present / absent / not mentioned, with body regions and a quote |
| `extract.py` | Gemini turns a note into findings (structured output, cached in `.cache/`); keyword fallback when there is no key |
| `score.py` | `combine()` merges a patient's notes; `score()` applies `rules.json` and the Gold Coast pattern |
| `rules.json` | Weights, thresholds and recommendation wording, editable without code |
| `timeline.py` | Runs a patient's notes in date order and reports the first date flagged |

Interfaces for the app are in [docs/interfaces.md](docs/interfaces.md).

## Team
BioHacks 2026, McMaster University, Detection and Diagnostics track.
