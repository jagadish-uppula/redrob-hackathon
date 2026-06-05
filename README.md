# Redrob Candidate Ranker

> Intelligent Candidate Discovery & Ranking Challenge — Submission by **U Jagadish**

A JD-agnostic, feature-based candidate ranking system that scores and ranks
100,000 candidates for a given job description. Built with pure Python stdlib —
no ML frameworks, no LLMs, no external APIs.

## Quick Start

### Prerequisites
- Python 3.11.4
- No additional packages required for ranking (only stdlib)

### Generate the submission

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

This will:
1. Load all 100,000 candidates from `candidates.jsonl`
2. Extract features from each candidate profile
3. Score and rank all candidates against the JD
4. Select the top 100 and generate reasoning
5. Write `submission.csv`

**Runtime**: ~2 minutes on CPU (well within the 5-minute limit)
**Memory**: ~4 GB peak (well within 16 GB limit)
**Network**: Zero external calls

### Validate the submission

```bash
python validate_submission.py submission.csv
```

### Run the Streamlit demo

```bash
pip install streamlit
streamlit run app.py
```

## Architecture

```
rank.py                     ← Main CLI entry point
├── src/
│   ├── config.py           ← All weights, thresholds, keyword dictionaries
│   ├── jd_parser.py        ← JD → structured requirements (generalizable)
│   ├── features.py         ← Candidate → numerical feature vector
│   ├── honeypot.py         ← Honeypot detection (6 heuristic checks)
│   ├── scorer.py           ← Feature vector → final score + penalties
│   └── reasoning.py        ← Score + candidate → reasoning string
├── app.py                  ← Streamlit demo app
├── submission_metadata.yaml
├── requirements.txt
└── validate_submission.py  ← Official format validator
```

## Methodology

### Scoring Components

| Component | Weight | What it measures |
|---|---|---|
| **Title Match** | 28% | Current title alignment with target role (primary anti-trap signal) |
| **Career Relevance** | 24% | Career description keywords + production deployment + company type |
| **Behavioral Signals** | 18% | Response rate, activity recency, notice period, platform engagement |
| **Skills Match** | 12% | Must-have/nice-to-have skills with trust validation |
| **Experience Fit** | 8% | Gaussian scoring centered on JD's ideal range (5–9 years) |
| **Education** | 5% | Institution tier + field relevance |
| **Location** | 5% | Geographic proximity to preferred cities |

### Anti-Trap Defenses

1. **Title-first filtering**: Non-tech titles (HR, Marketing, Accounting, etc.) receive a near-zero title score, preventing keyword stuffers from ranking high regardless of their skill list.

2. **Skill trust validation**: Cross-references claimed proficiency with duration months, endorsement counts, and platform assessment scores. "Expert" with 0 months = red flag.

3. **Honeypot detection**: Six heuristic checks catch impossible profiles:
   - Expert skills with zero duration
   - Too many expert-level skills (8+)
   - Assessment scores contradicting proficiency
   - Career duration vs stated experience mismatch
   - Title-skill extreme mismatch
   - Impossible company tenure

4. **Consulting-only penalty**: Candidates with entire careers at services firms (TCS, Infosys, Wipro, etc.) receive a 75% score reduction.

5. **Career description analysis**: Actually reads job descriptions to check for production deployment, retrieval/search/ranking work — not just keyword lists.

### Generalizability

The system is designed to work with **any job description**, not just this specific one:
- `jd_parser.py` converts any JD text into a structured `JDRequirements` object
- `config.py` holds all tunable parameters in one place
- The scoring engine only sees `JDRequirements` — never raw JD text

For this hackathon, the JD requirements are encoded in `jd_parser.build_senior_ai_engineer_jd()`.

## Compute Constraints Compliance

| Constraint | Limit | Actual |
|---|---|---|
| Runtime | ≤ 5 minutes | ~2 minutes |
| Memory | ≤ 16 GB RAM | ~4 GB peak |
| Compute | CPU only | ✅ No GPU |
| Network | Offline | ✅ No API calls |
| Dependencies | Minimal | Python stdlib only |

## License

Hackathon submission — all rights reserved.
