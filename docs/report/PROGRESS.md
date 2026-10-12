# Progress — built / in progress / remaining

Taken from repo state at commit `9d5b0bf`, 2026-10-12. Source for each line is given; nothing
here is an estimate unless explicitly labelled one.

## Built (M1 complete)

| Item | Evidence | Date landed |
|---|---|---|
| High-Level Design, frozen at v2.11 | `docs/HLD.md` | 2026-10-08 → 2026-10-12 (last change log entry) |
| `core/` — all 12 M1 modules | `ls backend/src/core` | Phases 2–6a, 2026-10-08 → 2026-10-11 |
| `app/` shared edge (`data.py`, `render.py`, `view.py`, `audit.py`) | `ls backend/src/app` | sprint block S3, 2026-10-11 |
| CLI (the HARD GATE: a full session plays with no web layer) | `backend/src/cli.py` | sprint block S3, commit `aa65e07`, 2026-10-11 |
| API — 4 endpoints, TypeAdapter schemas, one error envelope | `backend/src/api/` | sprint blocks S4/S4.1, commits `e409dd7`/`b38f86f`, 2026-10-11 |
| Facts confirmation screen + `confirm_facts` (section 14 safety net) | `backend/src/core/tutor.py`, `session.py` | commit `6d0e082`, 2026-10-12 |
| React frontend M1 — Read & Facts, Prove, Explanation | `frontend/src/` | commit `caedfec`, 2026-10-12 |
| Pilot E5 tooling — protocol, consent, pre/post tests, `analyze_pilot.py` | `docs/pilot/` | commit `8b76db3`, 2026-10-12 |
| `run_experiments.py` — simulation, T2 hint soundness, T3 search cost | `scripts/run_experiments.py` | commit (S8 part 2), 2026-10-12 |
| `heldout_eval.py` — ready, awaiting the human-written input file | `scripts/heldout_eval.py` | commit `1d7d96d`, 2026-10-12 |
| Pilot event log (opt-in, edge-only) + Pilot ID persistence + Edit-facts path | `backend/src/api/main.py`, `frontend/src/` | commits `e66ca25`, `9d5b0bf`, 2026-10-12 |
| `test_no_builtin_hash` (AST guard) | `backend/tests/test_no_builtin_hash.py` | commit `bc13c5a`, 2026-10-12 |
| 804 passing tests, 0 failing | `python -m pytest backend/tests -q` → `804 passed, 1 skipped` | re-run 2026-10-12 |
| Mutation testing — core M1 modules (82/82 caught) | `docs/experiments/mutation_log.md` | Phase 6a, 2026-10-11 |
| Differential testing — 940/940 agreement | `docs/experiments/differential.md` | v2.9, 2026-10-09/10 |
| Search latency characterised and bounded | `docs/experiments/search_latency.md` | v2.9 A3, 2026-10-10 |
| CI green on last 20 pushes | `gh run list --branch main --limit 20` | checked 2026-10-12 |

## In progress

| Item | Status | Evidence |
|---|---|---|
| Mutation testing for S1–S8 modules (`tutor.py` rewrite, `session.py`, API, frontend, pilot tooling) | **not yet run** — scheduled as sprint block S9 | `docs/experiments/mutation_log.md`'s last table is Phase 6a, commit `f1eaf28`; nothing since |
| This report support kit | in progress — this directory | `docs/report/` |

## Remaining (not started)

| Item | Why it matters | Evidence it is not started |
|---|---|---|
| M2 core: `core/translation.py`, `core/narrate.py` | The Translate stage, formula equivalence checking, and prose explanation are entirely M2 scope | files do not exist: `ls backend/src/core` has no `translation.py`/`narrate.py` |
| M2 frontend: the Translate stage UI | depends on the M2 API action | `backend/src/api/main.py`'s `_translate` handler still `raise NotImplementedUntilM2` |
| `data/heldout_paragraphs.json` (T1 evaluation) | must be written by humans, post-freeze, never by Claude (CLAUDE.md rule 6) | file does not exist; `scripts/heldout_eval.py` reports "not yet run" when executed |
| The pilot session itself | the tooling is ready but no participant has run through it yet | `docs/pilot/template.csv` has a header row only; `docs/pilot/logs/` is empty/absent |
| Wiring or disposing of `data/eval/*.json` | two 15-item AI-generated evaluation sets exist on disk, untracked by git, with no script reading them | `git status --short data/eval/` → `?? data/eval/`; `grep -rl "data/eval" --include="*.py" .` → no matches |
| `docs/misconceptions.md`, `docs/report/REPORT_OUTLINE.md`'s guiding-question answers, report prose | human-only content per CLAUDE.md's academic integrity section | not written (and must not be written by Claude) |
| `docs/screenshots/` | needed for `FACTS.md` §9's architecture section | directory does not exist |
| Final audit + `progress-v1` tag | the sprint's own exit condition | tag does not exist: `git tag --list progress-v1` → empty |

## Dates, summarised

- **2026-10-08:** Phase 0 (design) and Phase 1 (scaffold) — `docs/HLD.md` begins, repo created.
- **2026-10-08 → 2026-10-11:** Phases 2–6a — core modules built and mutation-tested one at a
  time, test-first.
- **2026-10-11:** Sprint re-baseline (budget policy change); sprint blocks S1–S4.1 — tutoring
  policy, exercise bank, CLI, API, hardening.
- **2026-10-12:** Facts-stage-skip fix; sprint block S5 (frontend M1); sprint block S8 (pilot
  tooling, experiment scripts); pilot-freeze prep (pilot ID persistence, Edit-facts path).
- **Not yet dated:** sprint block S6/S7 (M2), S9 (mutation pass on new modules), S10 (this
  report kit — in progress now), S11 (final audit and tag).
