# Report outline — guidance only, no prose

This file does **not** contain report text. Per the academic integrity rules governing this
project, Claude may provide facts, templates, and guiding questions — the problem statement,
objectives, literature review, limitations narrative, methodology narrative, analysis, and
conclusions must be written by the students in their own words. Every "guiding question" below
is something *you* answer, not something answered for you.

Evidence paths referenced throughout point into `docs/report/FACTS.md` and the rest of this
repository — read the relevant fact before writing the paragraph that cites it.

---

## 1. Problem Statement

**What she's asking for:** a clear, specific statement of the gap or need this project addresses
— not a restatement of what the system does, but *why it needs to exist*.

**Guiding questions:**
1. What specific difficulty do students have with propositional-logic proofs that existing tools
   (a plain truth-table calculator, a textbook, a human tutor) don't address well?
2. Why does *step-level* feedback (naming the exact mistake) matter more than a single
   right/wrong grade for this subject? (See `docs/HLD.md` §1 for the design rationale you can
   reference, in your own words.)
3. What is explicitly **out of scope** (free-form English, first-order logic, accounts, a
   database — `CLAUDE.md`'s "DO NOT BUILD" list), and why does stating that scope sharpen the
   problem statement rather than weaken it?
4. Who is the user — the "3rd year AI course" framing in `README.md` suggests a specific
   audience. Who exactly, and what do they already know coming in?

**Repo evidence to cite:** `docs/HLD.md` §1 (Purpose, Problem, Formative Angle); `README.md`'s
opening paragraph and syllabus mapping line.

**Suggested length:** half a page to one page.

**Common mistakes:** describing the *solution* instead of the *problem*; a problem statement so
generic it would fit any tutoring system, not specifically a propositional-logic one.

---

## 2. Objectives

**What she's asking for:** specific, checkable objectives — not aspirations. The strongest
objectives you can write are the ones the system already demonstrably satisfies, because you can
point at the exact evidence.

**Measurable facts the system satisfies, each with its evidence file — use these to phrase your
objectives in your own words (do not copy these sentences verbatim):**

| Fact | Evidence |
|---|---|
| Parses a controlled English grammar into propositional clauses with 7 named, distinguishable error codes (never a silent guess) | `docs/HLD.md` §3; `backend/src/core/english.py`; `test_connective_inside_fact_mis_splits_visibly` |
| Decides entailment exactly by truth table (not by search, not by approximation) | `backend/src/core/entail.py`; differential testing agrees with resolution 940/940 (`docs/experiments/differential.md`) |
| Finds the *shortest* resolution refutation by exact BFS, with a measured and bounded work budget | `backend/src/core/search.py`; `docs/experiments/search_latency.md` |
| Diagnoses a wrong resolution step as one of 6 named mistakes, never just "wrong" | `backend/src/core/logic.py`; `data/messages.yaml`'s `step:` group |
| Tracks 3 skills per student via Bayesian Knowledge Tracing and selects the next exercise from that state | `backend/src/core/bkt.py`, `tutor.py` |
| Shows the student every extracted fact before any proving begins, so a parser mis-split is visible rather than silent | `docs/HLD.md` §14 item 2; `backend/src/core/session.py`'s Facts stage |
| Plays a complete practice session with zero web layer (the CLI "hard gate") | `backend/src/cli.py`; `docs/experiments/cli_transcript.md` |
| Serves the same logic through a 4-endpoint stateless HTTP API and a React frontend | `backend/src/api/`; `frontend/src/` |
| 804 tests pass; 82 mutation-tested core mutants all caught (as of Phase 6a) | `FACTS.md` §3–4 |

**Guiding questions:**
1. Which 3–5 of the facts above are you actually claiming as *objectives* (stated before you
   built anything) versus *results* (things you measured after)? Keep these distinct.
2. What objective did you **not** meet yet, and is that because it's M2 scope (not started) or
   because it genuinely failed? (`PROGRESS.md`'s "Remaining" table is the honest list.)
3. Are your objectives falsifiable — could a reader check each one against the repo and find it
   either true or false?

**Repo evidence to cite:** the table above; `docs/HLD.md` §2 (Milestones, Scope, Budgets).

**Suggested length:** 5–8 bullet points, half a page.

**Common mistakes:** objectives that are really just features restated as goals; claiming an M2
objective (translation checking, narrated explanations) as already met when `PROGRESS.md` shows
it isn't built.

---

## 3. Literature Review (25–30 articles)

**What she's asking for:** a synthesized discussion of prior work, organized by theme, with your
own critical evaluation of each — not a list of summaries.

**Guiding questions:**
1. Group the papers in `literature_matrix.csv` by the `theme` column. What themes emerge
   (knowledge tracing, ITS effectiveness meta-analyses, feedback theory, logic-tutor hint
   generation, open learner models)? Does your grouping match the matrix's themes, or would you
   group them differently — and why?
2. For the knowledge-tracing cluster (L02–L08): what's the actual disagreement in this
   literature — is BKT still competitive with deep learning, or not? (L06 vs. L07 and L08 give
   you both sides — read them, don't just cite the finding column.)
3. For the "ITS actually works" cluster (L10–L12): these are three different meta-analyses
   reporting different effect sizes. Why might they differ (different inclusion criteria,
   different outcome measures)? What does that tell you about how confidently you can cite "ITS
   works" as a blanket claim?
4. L18 and L19 (Barnes/Stamper, Stamper/Eagle/Barnes/Croy) are the closest prior work to
   ProofPilot — a logic-proof tutor with automatically generated hints. How does ProofPilot's
   hint ladder (rule/search-derived, not data-mined from historical student attempts) differ
   from theirs, and what's the tradeoff?
5. The matrix has **only 24–25 verified entries** against the 25–30 target. Which 2–6 more
   papers will you add, and from which theme are they missing? (Candidates: more on open learner
   models beyond L20; a paper specifically on formative assessment in STEM; a paper on
   controlled/restricted natural language grammars if you want to support §5's parsing design.)
6. What is your own critical take on each paper you actually read — fill in
   `literature_matrix.csv`'s `my_critical_summary` column yourself; it is intentionally blank.

**Repo evidence to cite:** `literature_matrix.csv` in full; `references.md` for the formatted
citation list.

**Suggested length:** 2–3 pages of synthesized prose, organized by theme, not by paper.

**Common mistakes:** one paragraph per paper ("Smith et al. found X. Jones et al. found Y.")
instead of synthesis; citing a paper's abstract without having read enough to critique it; citing
more papers than you've actually read (the `read(Y/N)` column exists to keep you honest about
this).

---

## 4. Limitations of Existing Systems

**What she's asking for:** what's wrong with, or missing from, prior approaches — setting up why
ProofPilot's specific design choices were necessary.

**Guiding questions:**
1. Based on the literature review, what do existing ITS/logic tutors get wrong or leave
   unaddressed that your literature matrix's `limitation` column surfaces?
2. L06's deep-knowledge-tracing limitation (disputed replication) and L08's note (access-gated,
   so its own limitations couldn't be confirmed from the abstract) are both honestly incomplete
   in this matrix — what does that tell you about how confidently the literature review can
   characterize "existing systems," and how should you phrase that honestly in your own
   limitations section?
3. Separately from the *literature's* limitations: `docs/HLD.md` §14 lists ProofPilot's **own**
   11 known limitations (reproduced in `FACTS.md` §9). Which of those are limitations *inherited*
   from the general approach (e.g. the grammar-vs-free-English tradeoff is a limitation of every
   controlled-grammar system, not just this one) versus limitations *specific to this
   implementation* (e.g. the naive suffix stripper)?

**Repo evidence to cite:** `literature_matrix.csv`'s `limitation` column; `FACTS.md` §9's Known
Limitations list (verbatim from `docs/HLD.md` §14).

**Suggested length:** half a page to one page.

**Common mistakes:** restating ProofPilot's own limitations here instead of existing systems' (that
belongs in §7's Experimental Analysis or a dedicated limitations section, depending on her exact
rubric — check which section she wants it in); vague claims ("existing tools are not adaptive")
without a cited paper backing the claim.

---

## 5. Proposed Methodology

**What she's asking for:** how the system works, in enough technical detail that a reader could
reconstruct the approach — architecture, algorithms, data flow.

**Guiding questions:**
1. Walk through the 6-stage pipeline (`FACTS.md` §9: parse → facts → consistency → entailment →
   relevance → proof) in your own words. Why does the order matter — what would break if
   `relevance` ran before `consistency`? (The answer is in `docs/HLD.md` §7, in your own words,
   not copied.)
2. Explain the resolution-refutation algorithm your search implements, and why exact BFS (not a
   heuristic search) was chosen. What's the complexity tradeoff, and how does the measured
   search-latency table (`FACTS.md` §7) support or complicate that choice?
3. Explain Bayesian Knowledge Tracing in your own words: what does the system believe about a
   student, how does one observation update that belief, and why does a BKT system need a
   mastery-slack clamp (`docs/HLD.md`'s discussion of `MASTERY_SLACK`)?
4. The architecture diagram (`FACTS.md` §9) separates `core/` (pure Python, no web imports) from
   the API/CLI/frontend adapters. Why does that separation matter for correctness, not just code
   organization — what bug class does it prevent?
5. **If the brief specifically asks for a "9-stage pipeline"** and you intended something
   different from the 6-stage ordering in `docs/HLD.md` §7, clarify with your professor which
   structure she means — `FACTS.md` flags this discrepancy rather than inventing a 9th stage to
   match an unconfirmed brief.

**Repo evidence to cite:** `FACTS.md` §9 (architecture diagram, module table, pipeline order);
`docs/HLD.md` §6 (Algorithms, with each one's correctness argument) and §7.

**Suggested length:** 2–3 pages, with the architecture diagram included.

**Common mistakes:** describing *what* each module does without explaining *why* it's structured
that way; omitting the correctness argument for the pipeline ordering (it's not just
"organized," it's required for correctness — §7 states this directly).

---

## 6. Code Repository

**What she's asking for:** confirmation the code exists, is organized, and is accessible —
usually just a link plus a short structural description.

**Guiding questions:**
1. State the repo URL and the commit hash you're reporting against (`FACTS.md` §1 has both).
2. Briefly describe the top-level layout (`backend/`, `frontend/`, `data/`, `docs/`, `scripts/`,
   `tools/`) — one line each is enough here; the detail belongs in §5.
3. Point to the CI badge/status and explain in one sentence what it verifies (tests, lint,
   budgets — `FACTS.md` §1's CI table).

**Repo evidence to cite:** `FACTS.md` §1.

**Suggested length:** a few sentences plus the link. This section is short by design.

**Common mistakes:** padding this section with content that belongs in §5 or §7.

---

## 7. Experimental Analysis and Current Progress

**What she's asking for:** what you measured, what it shows, and honestly, what's still
incomplete.

**Guiding questions:**
1. Walk through the simulation table (`FACTS.md` §6): what does "premature-release rate" mean in
   plain language, and why is it the right metric rather than mean exercises or final mastery at
   a fixed budget? (The caveats section explains why those alternatives were rejected — restate
   the reasoning in your own words, not the caveat text verbatim.)
2. **State the mismatched-arm result correctly**: it used 11.51 exercises on average vs. the
   baseline's 8.00 — it is *not* a budget-matched comparison. The honest claim is "the adaptive
   rule still keeps premature release low (4.8%) even when the model is misspecified, at the
   cost of roughly 50% more practice" — not "it beats the baseline at an equal budget."
3. What does the mutation-testing table (`FACTS.md` §4) actually demonstrate, and what doesn't
   it demonstrate? (It shows the *tests* can detect *known, injected* defects — it says nothing
   about defects nobody thought to inject.)
4. What does 940/940 differential agreement mean, concretely — two independent methods (truth
   table and resolution) agreeing on every one of 940 generated test cases. Why does that matter
   more than either method's own unit tests passing?
5. What is genuinely **not yet available** — be as specific as `PROGRESS.md`'s "Remaining"
   table, and say so plainly rather than implying it's done. (The pilot hasn't run. The held-out
   evaluation hasn't run. M2 isn't built. Mutation testing hasn't covered the post-Phase-6a
   modules.)

**Repo evidence to cite:** `FACTS.md` §3–7 in full; `PROGRESS.md`.

**Suggested length:** 2–3 pages, including the simulation graph (`docs/results.png`) and at
least one other table.

**Common mistakes:** presenting the simulation as evidence that "students learn more" (HLD §14
item 9 explicitly says it isn't — it only tests the stopping rule under the model's own
assumptions); silently dropping the mismatched-arm caveat; reporting the Phase-6a mutation table
as if it covered modules built since then.

---

## 8. References (APA)

**What she's asking for:** a formatted, alphabetized reference list matching your in-text
citations.

**Guiding questions:**
1. Does every citation you used in §3 appear in `references.md`? Does every entry in
   `references.md` get cited somewhere in your text? (A reference list with uncited entries, or
   citations with no matching reference, is a common and easily avoidable error.)
2. For the ambiguous "Aleven et al. 2006" entry — did you resolve which paper you actually mean
   before submitting? `references.md` flags this with a note; remove the one you didn't use.

**Repo evidence to cite:** `references.md` (generated only from verified rows — do not add an
unverified entry here).

**Suggested length:** as long as your citation count requires; one page is typical for 25–30
references.

**Common mistakes:** mixing citation styles; citing a paper in text that isn't in the list, or
vice versa; including an unverified or invented reference (this document's integrity rules
explicitly forbid this — `literature_matrix.csv` only contains what was actually confirmed via a
DOI or publisher page).

---

## 9. Contribution Statement (with AI disclosure)

**What she's asking for:** who did what, honestly, plus a clear account of AI tool use.

**Guiding questions:**
1. Fill in `CONTRIBUTION_TEMPLATE.md`'s role table yourselves — every cell is marked "to be
   confirmed by students" on purpose. Don't let the prefilled draft stand as the final answer
   without actually discussing and agreeing it between the two of you.
2. `CONTRIBUTION_TEMPLATE.md` §2 shows all 70 commits under one git author identity. Address this
   directly and honestly in your contribution statement — don't let the report imply a
   contribution split the git history doesn't show, and don't let a true split go unexplained if
   one of you worked outside git commits (code review, testing, pilot facilitation).
3. The AI disclosure table in `CONTRIBUTION_TEMPLATE.md` §3 is prefilled from `AI_USAGE_LOG.md`
   and the git trailers for the parts that are checkable. Fill in the blanks (the claude.ai chat
   usage, the pilot-form revisions) honestly — these are genuinely things Claude Code running in
   this repository cannot know.
4. Complete the "human-written content" checklist (§3) with real names and dates once the
   held-out paragraphs and pilot sessions actually happen.

**Repo evidence to cite:** `CONTRIBUTION_TEMPLATE.md` in full; `AI_USAGE_LOG.md`.

**Suggested length:** half a page to one page, plus the filled-in tables.

**Common mistakes:** an AI disclosure that undersells the tool's role (the git trailers and
`AI_USAGE_LOG.md` make the true extent checkable, so understating it is both against the
integrity rules and easily caught); a contribution table that doesn't match the git fact table
without an explanation of the discrepancy.
