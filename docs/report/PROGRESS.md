# Progress — built / in progress / remaining

Taken from repo state at local commit `3b8c5ea`, 2026-10-25 (4 commits ahead of `fef68ba`, the
last one CI has actually verified — commit-locally-and-stop, awaiting "approved"). Source for
each line is given; nothing here is an estimate unless explicitly labelled one.

## Built

| Item | Evidence | Date landed |
|---|---|---|
| High-Level Design, frozen at v2.12 | `docs/HLD.md` | 2026-10-08 → 2026-10-25 (last change log entry) |
| `core/` — all 12 M1 modules | `ls backend/src/core` | Phases 2–6a, 2026-10-08 → 2026-10-11 |
| `core/` — all 3 M2 modules (`formula.py`, `translation.py`, `narrate.py`) | `ls backend/src/core` | commit `8d549d2`, 2026-10-24 |
| `app/` shared edge (`data.py`, `render.py`, `view.py`, `audit.py`) | `ls backend/src/app` | sprint block S3, 2026-10-11 |
| CLI (the HARD GATE: a full session plays with no web layer) | `backend/src/cli.py` | sprint block S3, 2026-10-11 |
| API — 4 endpoints, TypeAdapter schemas, one error envelope | `backend/src/api/` | sprint blocks S4/S4.1, 2026-10-11 |
| Facts confirmation screen + `confirm_facts` (section 14 safety net) | `backend/src/core/tutor.py`, `session.py` | commit `6d0e082`, 2026-10-12 |
| React frontend M1 — Read & Facts, Prove, Explanation | `frontend/src/` | commit `caedfec`, 2026-10-12 |
| Pilot E5 tooling — protocol, consent, pre/post tests, `analyze_pilot.py` | `docs/pilot/` | commit `8b76db3`, 2026-10-12 |
| `run_experiments.py` — simulation, T2 hint soundness, T3 search cost | `scripts/run_experiments.py` | commit (S8 part 2), 2026-10-12 |
| `heldout_eval.py` — ready, awaiting the human-written input file | `scripts/heldout_eval.py` | commit `1d7d96d`, 2026-10-12 |
| Pilot event log (opt-in, edge-only) + Pilot ID persistence + Edit-facts path | `backend/src/api/main.py`, `frontend/src/` | commits `e66ca25`, `9d5b0bf`, 2026-10-12 |
| `test_no_builtin_hash` (AST guard) | `backend/tests/test_no_builtin_hash.py` | commit `bc13c5a`, 2026-10-12 |
| **The `progress-v1` tag** | `git tag --list progress-v1` → points at `fef68ba` | 2026-10-24/25 |
| `data/eval/*.json` — the two AI-generated evaluation sets, committed and wired | `git ls-files data/eval/`; `scripts/ai_eval_tfl.py` → 15/15 agree | commits `d090e8f`, `a1649c2`, 2026-10-24/25 |
| Mutation testing — S1–S8 modules, the backlog PROGRESS.md used to list as "not yet run" (`session.py`, `tutor.py`, `config.py`) + the three new M2 modules, **43/43 caught** | `docs/experiments/mutation_log.md` | commit `fef68ba`, 2026-10-25 |
| `core/tutor.py`'s `translate_trigger` + `core/session.py`'s `record_translation` (M2 evidence wiring) | `backend/src/core/tutor.py`, `session.py` | commit `9a9b0b4`, 2026-10-24 |
| **Design change: Translate is universal, not M2-conditional** (HLD v2.12) | `docs/HLD.md` §16; `tutor.TRANSITIONS` | commit `f236863`, 2026-10-25 |
| **Minimal fix: Translate auto-skips when nothing needs it** — restores pre-v2.12 behaviour for every exercise today | `backend/src/core/session.py` `enter_stage` | commit `3b8c5ea`, 2026-10-25 |
| 842 passing tests, 0 failing, both hash seeds | `python -m pytest backend/tests -q` → `842 passed, 1 skipped` | re-run 2026-10-25 |
| Differential testing — 940/940 agreement | `docs/experiments/differential.md` | v2.9, 2026-10-09/10, regression-checked 2026-10-25 |
| Search latency characterised and bounded | `docs/experiments/search_latency.md` | v2.9 A3, 2026-10-10, unaffected by any change since |

## In progress

| Item | Status | Evidence |
|---|---|---|
| **The real M2 Translate check** — a reference-formula renderer, 6 `messages.yaml` entries, `app/render.py`'s translate method, `api/main.py`'s real `_translate` handler, `frontend/src/TranslateStep.jsx` | **deferred, explicitly, not hidden** — the stage machine, evidence wiring and attempt-record plumbing are all built and ready for it | `docs/HLD.md`'s v2.12 change-log entry states the budget reason (`core_session` would cross its cap; `api_cli` is already over its ceiling) |
| This report support kit | in progress — this directory | `docs/report/` |

## Remaining (not started)

| Item | Why it matters | Evidence it is not started |
|---|---|---|
| `data/heldout_paragraphs.json` (T1 evaluation) | must be written by humans, post-freeze, never by Claude (CLAUDE.md rule 6) | file does not exist; `scripts/heldout_eval.py` reports "not yet run" when executed, re-verified 2026-10-25 |
| The pilot session itself | the tooling is ready but no participant has run through it yet | `docs/pilot/template.csv` has a header row only; `python scripts/analyze_pilot.py` → `N = 0 participants`, re-verified 2026-10-25 |
| `docs/misconceptions.md`, `docs/report/REPORT_OUTLINE.md`'s guiding-question answers, report prose, the Contribution Statement | human-only content per CLAUDE.md's academic integrity section | not written (and must not be written by Claude) |
| `docs/screenshots/` | needed for `FACTS.md` §9's architecture section | directory does not exist |
| **Pushing the 4 local commits past `fef68ba`** | the absolute per-gate push rule — needs "approved" for this specific gate | `git log origin/main..HEAD` → 4 commits not on `origin/main` |
| The 34-entry `AI_USAGE_LOG.md` "what the student changed by hand: to confirm" backlog | the student is filling this in separately, not as part of this report | per the student's explicit instruction, not touched tonight |

## Dates, summarised

- **2026-10-08:** Phase 0 (design) and Phase 1 (scaffold) — `docs/HLD.md` begins, repo created.
- **2026-10-08 → 2026-10-11:** Phases 2–6a — core M1 modules built and mutation-tested one at a
  time, test-first.
- **2026-10-11 → 2026-10-12:** Sprint re-baseline; sprint blocks S1–S8 — tutoring policy,
  exercise bank, CLI, API, hardening, frontend M1, pilot tooling, experiment scripts, pilot-freeze
  prep. Tagged standing approval for a full-scope sprint to `progress-v1`.
- **2026-10-24:** S6 — the three M2 core modules (`formula.py`, `translation.py`, `narrate.py`).
  S10 — the report support kit and deck.
- **2026-10-24 → 2026-10-25 (S11, post-`progress-v1` gate):** CI unblocked (committed the
  AI-generated eval sets); mutation refresh across 6 modules (43/43, two survivors fixed);
  `translate_trigger`/`record_translation` wiring; `progress-v1` tagged; the Translate-universal
  design change (HLD v2.12); the minimal auto-skip fix; this `FACTS.md`/`PROGRESS.md` refresh.
