# ProofPilot

Step-level formative feedback for propositional logic arguments, built with controlled-English
parsing, truth tables, resolution refutation, BFS and Bayesian Knowledge Tracing.

> **Status: M1 complete, M2 core modules built.** The design is frozen at
> [`docs/HLD.md`](docs/HLD.md) v2.14. Backend, frontend and CLI all run end to end — see
> [Run the app](#run-the-app) below. Current progress: [`docs/report/FACTS.md`](docs/report/FACTS.md).

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

## Run the app

Two servers, started separately (two terminals). Needs the backend venv from
[Quick start](#quick-start-windows-powershell) above, plus Node 18+ for the frontend.

**Backend** (serves the API on `http://127.0.0.1:8000`):

```powershell
cd backend
..\.venv\Scripts\Activate.ps1   # if not already active
python -m uvicorn src.api.main:app --reload
```

**Frontend** (serves the UI on `http://localhost:5173`, pinned — see `frontend/vite.config.js`):

```powershell
cd frontend
npm install     # first time only
npm run dev
```

Open `http://localhost:5173`. The frontend calls the backend at `127.0.0.1:8000` by default
(`frontend/src/api.js`; override with the `VITE_API_URL` env var if the backend runs elsewhere).
CORS is pinned to exactly this origin and `http://127.0.0.1:5173` — a different port fails with a
browser error that does not mention CORS (see `backend/src/api/main.py`).

**CLI** (no web layer at all — the HARD GATE a full practice session must pass):

```powershell
cd backend
python -m src.cli
```

## Honest limitations of the API

**The session lives on the client, and the client can edit it.** ProofPilot is stateless by
design: the whole session travels in every request body and the browser keeps it in
`localStorage`. That makes the server simple and a reload harmless, and it means a determined
student can open the developer console and change their own mastery scores.

The server validates **structure and range**, not **integrity**. A request is refused if it is
not a well-formed session, if it names a clause that is not on the board, if it uses a symbol
belonging to no fact in the exercise, if it carries more clauses or literals than the limits
allow, or if a mastery value falls outside the interval the model is defined on. None of that
proves the session is one the server previously issued — only that it is one the server *could*
have issued.

**This is acceptable here, and it is a deliberate choice rather than an oversight.** ProofPilot is
a practice tool: nothing it records is graded, and the only person a student can mislead by
editing their own mastery is themselves. Making the session tamper-*proof* needs the server to
sign what it issues and verify the signature on the way back, which means a key to manage and a
second failure mode to handle — cost with no benefit for a tool that awards nothing.

**It would have to change before any use where the record matters.** Signing the session, or
holding it server-side behind a session id, is the future work; the design note is in
`docs/HLD.md` §8, and the range and structure checks are tested one request each in
`backend/tests/test_api.py`.

## Repository layout

| Path | Contents |
|---|---|
| `backend/src/core/` | All logic — pure Python, no web imports |
| `backend/src/api/` | FastAPI layer: 4 endpoints, schemas, error mapping |
| `backend/tests/` | pytest suite |
| `data/` | `exercises.json`, `heldout_paragraphs.json`, `messages.yaml` |
| `scripts/` | Difficulty computation, experiments, held-out evaluation |
| `frontend/` | React + Vite UI, built (M1 stages; M2's Translate step deferred, see HLD v2.14) |
| `docs/` | `HLD.md` (source of truth), review, experiment results, report support kit |

## Documents

- **[`docs/HLD.md`](docs/HLD.md)** — high-level design v2.14, frozen. Architecture, grammar,
  algorithms with correctness arguments, API contract, budgets, and a verification report.
- **[`docs/HLD_REVIEW.md`](docs/HLD_REVIEW.md)** — adversarial review of the v1 design (historical).
- **[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md)** — factual record of AI assistance, updated every phase.

## AI assistance

This project was built with AI assistance (Claude Code). Every use is logged factually in
[`AI_USAGE_LOG.md`](AI_USAGE_LOG.md). No report prose was AI-generated; the report text is the
students' own work, and the contribution statement discloses the extent of AI use.

## License

MIT — see [`LICENSE`](LICENSE).
