# Reading Guide

Which parts of `docs/HLD.md` to read, and when. **Section numbers and titles only** — no design
content is repeated here, so this file cannot drift out of date when the HLD changes.

Derived from **HLD v2.7** (frozen 2026-10-08). Ownership roles are defined in HLD §4.1.
`backend/tests/test_docs_version.py` fails if this reference goes stale.

## Everyone, before writing any code

| § | Title |
|---|---|
| 1 | Purpose, Problem, Formative Angle |
| 2 | Milestones, Scope, Budgets |
| 4 | Architecture (incl. §4.1 Module ownership) |
| 7 | Mandatory Pipeline Ordering |
| 14 | Known Limitations |
| 17.11 | Viva readiness — 3 sentences per module |

Plus `CLAUDE.md` in full. It is short and it is the rules.

## By phase

| Phase | Read before starting | Also check |
|---|---|---|
| 2 — `logic.py` | §6.7 Resolution diagnosis | §10 (test names), §13.4 (line budget) |
| 3 — `search.py` | §6.6 Search, §6.6.1 Hints when the conclusion does not follow | §17.6 Search re-check |
| 4 — `english.py` | §3 Supported-Language Specification, §6.1 Parsing | §17.2 Grammar audit |
| 4 — `facts.py` | §6.3 Fact normalization | §17.4 Normalization audit |
| 4 — `cnf.py` | §6.2 CNF | §17.3 Logic audit |
| 5 — `entail.py` | §6.4 Entailment | §17.5 Correctness arguments |
| 5 — `relevance.py` | §6.5 Relevance filter | §7 Pipeline ordering |
| 6 — `bkt.py`, `tutor.py` | §6.8 BKT, §9 Evidence Mapping | §17.7 BKT re-check |
| 7 — CLI | §5 Data Model and State | §2 (M1 scope) |
| 8 — API | §8 API Contract and Error Model | §17.8 API audit |
| 9 — Frontend | §5 Data Model, §8 API Contract | §13.4 (frontend budget) |
| 10 — Experiments | §11 Evaluation Plan | §17.10 Determinism audit |
| 11 — Report kit | §12 Design Decisions, §14 Known Limitations | §16 Change Log |

## By owner (HLD §4.1)

- **Member A** — own §3, §6.1, §6.2, §6.3, §6.4, §6.5 and their audits (§17.2–17.5).
- **Member B** — own §6.6, §6.6.1, §6.7, §6.8, §8, §9 and their audits (§17.6–17.8).
- **Both** — read the other's sections before that phase's gate. Both members must be able to
  explain every module (HLD §2); the joint walkthroughs that deliver this are budgeted in §13.3.

## Before the viva

Re-read §17.11 (three-sentence explanation per module), §17.9 (scenario traces), §12 (why each
decision was made and what was rejected), and §14 (what the system honestly cannot do).
