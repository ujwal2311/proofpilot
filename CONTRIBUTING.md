# Contributing

Two-member project. Module ownership is in `docs/HLD.md` §4.1; what to read before each phase is
in `docs/READING_GUIDE.md`.

## Branches

- `feat/<module>` — e.g. `feat/logic`, `feat/search`, `feat/english`.
- `fix/<short-description>` for defects, `docs/<short-description>` for documentation only.
- Never commit to `main` directly once Phase 2 starts.

## Pull requests

- **Small.** One module or one concern per PR. A PR that touches `logic.py` and the frontend is
  two PRs.
- **CI must be green** — all six jobs (4 matrix, determinism, lint). Do not merge on a red or
  pending run.
- **The other member reviews before merge.** Both of us must be able to explain every module in
  the viva (`CLAUDE.md`), so review is how that actually happens, not a formality.
- Reviewer checks: does it match the HLD section it implements, are the tests real (would they
  fail if the code were wrong), and does it stay inside the line budget for that bucket.

## Commits

- Subject: imperative, ≤ 72 characters, no trailing full stop — `Add resolvent diagnosis order`.
- Body: explain **why**, not what. The diff shows what.
- **AI-assisted commits keep the `Co-Authored-By:` trailer.** This is an academic-integrity
  requirement, not a style preference — the contribution statement and `AI_USAGE_LOG.md` must
  agree with the git history.

## Before you push

```powershell
python -m pytest
ruff check .
ruff format --check .
```

Branch protection is not enabled; we rely on this document and on review.
