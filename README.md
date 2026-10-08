# ProofPilot

Step-level formative feedback for propositional logic arguments, built with controlled-English
parsing, truth tables, resolution refutation, BFS and Bayesian Knowledge Tracing.

> **Status: Phase 1 (scaffold).** The design is frozen at [`docs/HLD.md`](docs/HLD.md) v2.2.
> No logic is implemented yet — this README is a stub and grows at Phase 9.

A college AI course project (3rd year) by **CVS Ujwal** (24BCE0667) and **Keshav Raj**
(24BCI0306). Syllabus mapping: Unit 2 Search (BFS), Unit 4 Logic (resolution, refutation),
Unit 5 Uncertainty (Bayes' rule, BKT).

## What it will do

Read a short English paragraph and a claimed conclusion, show you the facts it extracted and let
you correct them, decide by truth table whether the conclusion actually follows, then coach a
resolution refutation step by step — naming the exact mistake in each wrong step and offering
progressive hints computed from your current clause set. BKT tracks three skills (CLASH, RESOLVE,
STRATEGY) to choose the next exercise and decide when you are done.

It supports one precisely documented controlled grammar, not free-form English, and refuses
anything outside it with a named error and a rephrasing hint. See
[`docs/HLD.md`](docs/HLD.md) §3 for the supported language and §14 for the honest limitations.

## Setup (Windows PowerShell)

```powershell
git clone https://github.com/ujwal2311/proofpilot.git
cd proofpilot

python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
python -m pip install -r requirements.txt

python -m pytest
```

Requires Python 3.11+ (developed on 3.12.10) and, from Phase 7, Node 18+.

## Repository layout

| Path | Contents |
|---|---|
| `backend/src/core/` | All logic — pure Python, no web imports |
| `backend/src/api/` | FastAPI layer: 4 endpoints, schemas, error mapping |
| `backend/tests/` | pytest suite |
| `data/` | `exercises.json`, `heldout_paragraphs.json`, `messages.yaml` |
| `scripts/` | Difficulty computation, experiments, held-out evaluation |
| `frontend/` | React + Vite UI (Phase 7) |
| `docs/` | `HLD.md` (source of truth), review, experiment results, report support kit |

## Documents

- **[`docs/HLD.md`](docs/HLD.md)** — high-level design v2.2, frozen. Architecture, grammar,
  algorithms with correctness arguments, API contract, budgets, and a verification report.
- **[`docs/HLD_REVIEW.md`](docs/HLD_REVIEW.md)** — adversarial review of the v1 design (historical).
- **[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md)** — factual record of AI assistance, updated every phase.

## AI assistance

This project was built with AI assistance (Claude Code). Every use is logged factually in
[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md). No report prose was AI-generated; the report text is the
students' own work, and the contribution statement discloses the extent of AI use.

## License

MIT — see [`LICENSE`](LICENSE).
