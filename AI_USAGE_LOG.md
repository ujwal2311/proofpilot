# AI Usage Log — ProofPilot

Factual record only. No estimated percentages. One entry per phase/session.

---

**Date:** 2026-10-08
**Phase:** 0 — High-Level Design
**Tool:** Claude Code (Sonnet 5)
**Files created:** `docs/HLD.md` (v1.0)
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Initial architecture, module responsibilities, data model, core signatures, API
contract, flow of one `/api/step` call, design-decisions table, pre-mortem, test plan, and a
review of the original project spec for ambiguities/errors, ahead of any code.

---

**Date:** 2026-10-08
**Phase:** 0 — Adversarial Design Review
**Tool:** Claude Code (Sonnet 5)
**Files created:** `docs/HLD_REVIEW.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Independent adversarial review of `docs/HLD.md` v1.0 against the project brief —
requirements traceability, contract consistency, algorithm/math re-derivation, 12 scenario
walkthroughs, determinism/performance/scope audits, a findings table (6 BLOCKER, 12 MAJOR, 6
MINOR), and 5 open questions for the student. No code or HLD edits made in this step; the review
was superseded before its patch list was applied, because the student redirected scope to v2.0
(see next entry) rather than approving the v1 patch list.

---

**Date:** 2026-10-08
**Phase:** 0 — High-Level Design v2.0 (scope pivot)
**Tool:** Claude Code (Sonnet 5)
**Files created/modified:** `docs/HLD.md` (replaced v1.0 with v2.0, in place), `CLAUDE.md`
(created — did not previously exist), `AI_USAGE_LOG.md` (created).
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Full redesign adding a controlled-English parsing pipeline (sentence parsing, fact
extraction/merge-confirmation, student translation-checking, truth-table entailment, a relevance
filter, hybrid BFS/set-of-support search) in front of the v1 resolution tutor, per the student's
explicit instructions, which stated the new instructions override older documents where they
conflict. Carried forward every v1 decision still valid and every `docs/HLD_REVIEW.md` finding
that still applied (documented in `docs/HLD.md` §15 Change Log). Computed an honest hours/line
budget (§12) rather than asserting the stated ≤65h/≤650-line targets were met — the computed
total (~99h / ~1,028 core lines, after applying every cut the brief permits) exceeds both targets,
and this is flagged as the first of 5 Open Questions (§14) rather than silently resolved either
direction. `CLAUDE.md` was created fresh (it did not exist before this phase) with constraints
aligned to v2.0, and its "Changes from the original project brief" section lists every exact
deviation from the brief the student originally supplied. No code was written in this phase.

---

**Date:** 2026-10-08
**Phase:** 0 — High-Level Design v2.1 (decisions applied + adversarial re-verification)
**Tool:** Claude Code (Opus 5)
**Files modified:** `docs/HLD.md` (v2.0 → v2.1, replaced in place), `CLAUDE.md` (trimmed to rules
and constraints only; design detail removed and replaced by a pointer to `docs/HLD.md` v2.1),
`AI_USAGE_LOG.md` (this entry).
**What the student changed by hand:** none yet — to confirm. The student supplied all milestone
and open-question decisions (the M1/M2/stretch split, the budget caps, and answers to OQ1–OQ5)
and the list of 9 required fixes; Claude applied them and wrote the document.
**Purpose:** Applied the student's decisions — milestone split into M1 ("English-reading proof
tutor", must ship) and M2 ("Translation coach"); set-of-support search and Jaccard similarity
merge suggestions moved to stretch; BKT reduced to 3 skills in M1 with TRANSLATE added in M2;
translation diagnoses cut from 6 to 3; OQ2–OQ5 answers folded into the evidence mapping,
evaluation plan and budget sections. Applied the 9 student-specified fixes, including replacing
the 9-case CNF lookup with the textbook 3-step algorithm after a documented three-criterion
comparison, adding the relevance-filter correctness proof together with its mandatory
consistency-first pipeline ordering, narrowing the anti-hardcoding grep to content words of five
or more letters, and re-estimating every hour figure bottom-up per module with the student's
review-and-understand time included. Then performed an adversarial re-verification, written into
a new `docs/HLD.md` §17, covering requirements traceability, the grammar, the logic conventions
and their CNF output, fact normalization, correctness arguments and pipeline ordering, search,
BKT, the API contract, 14 end-to-end scenarios, determinism, viva readiness and budgets. That
re-verification found 7 BLOCKERs in the v2.0 design — most significantly that two bank exercises
have non-following conclusions whose empty clause is unreachable, so every hint request on them
would have exhausted the search to the node cap — and all 7 are fixed in v2.1 and recorded in its
Change Log. Budgets are reported as computed (66.25 h and roughly 945 core lines after all
permitted cuts, against caps of 65 h and 850 lines) rather than adjusted to fit the targets. No
code was written in this phase.
