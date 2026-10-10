# ProofPilot

Step-level formative feedback for propositional logic arguments, built with controlled-English
parsing, truth tables, resolution refutation, BFS and Bayesian Knowledge Tracing.

> **Status: Phase 1 (scaffold).** The design is frozen at [`docs/HLD.md`](docs/HLD.md) v2.9.
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

## Quick start (Windows PowerShell)

Developed and tested on **Python 3.12.10**. CI additionally runs 3.13 on Ubuntu and Windows.

```powershell
git clone https://github.com/ujwal2311/proofpilot.git
cd proofpilot

# Use the launcher to pin the version explicitly -- `python` may resolve to a different
# interpreter (a Microsoft Store stub, or an Anaconda base env) than you expect.
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pytest
```

Expected output: `1 passed` (more as phases land).

**If `Activate.ps1` is blocked** with *"running scripts is disabled on this system"*, allow it for
the current window only — this does not change machine-wide policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

**If your prompt starts with `(base)`**, Anaconda is active and its interpreter will shadow the
venv. Run `conda deactivate` before creating the venv, or `conda config --set auto_activate_base false`
to stop it activating in new shells.

**Check which interpreter you actually have** before reporting a problem:

```powershell
py -0p            # every installed version and its path
python --version  # what `python` currently resolves to
```

### Dependencies

| File | Contents | When |
|---|---|---|
| `requirements.txt` | fastapi, uvicorn, pydantic, pyyaml | runtime — enough to serve the API |
| `requirements-dev.txt` | the above **plus** pytest, httpx, matplotlib, ruff | development, tests, experiments |
| `constraints.txt` | every transitive package, pinned | always pass `-c constraints.txt` so an indirect release cannot change a build |

The supported Python version is declared once, in `pyproject.toml` (`requires-python`); CI tests
the floor and the next release. Node 18+ is needed from Phase 7.

`PIP_DISABLE_PIP_VERSION_CHECK=1` is set in CI. pip is deliberately **not** upgraded there — the
whole point of pinning is that the toolchain does not move underneath a build, and a nag about a
newer pip is not a reason to change it mid-project.

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

- **[`docs/HLD.md`](docs/HLD.md)** — high-level design v2.9, frozen. Architecture, grammar,
  algorithms with correctness arguments, API contract, budgets, and a verification report.
- **[`docs/HLD_REVIEW.md`](docs/HLD_REVIEW.md)** — adversarial review of the v1 design (historical).
- **[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md)** — factual record of AI assistance, updated every phase.

## AI assistance

This project was built with AI assistance (Claude Code). Every use is logged factually in
[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md). No report prose was AI-generated; the report text is the
students' own work, and the contribution statement discloses the extent of AI use.

## License

MIT — see [`LICENSE`](LICENSE).
