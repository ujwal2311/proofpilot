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

---

**Date:** 2026-10-08
**Phase:** 0 — High-Level Design v2.2 (student decisions applied; design frozen)
**Tool:** Claude Code (Opus 5)
**Files modified:** `docs/HLD.md` (v2.1 → v2.2), `CLAUDE.md` (caps updated), `AI_USAGE_LOG.md`.
**What the student changed by hand:** none — the student supplied all decisions in writing
(budget accepted for a 2-person team, core cap raised to 975, pilot kept in M1 as the final
activity, the exact three hint texts for non-entailing exercises, and the A/B module ownership
split) and Claude applied them.
**Purpose:** Applied the student's resolutions to the two open questions and added two new
requirements: a hint ladder for exercises whose conclusion does not follow
(`HINT_NOT_FOLLOW_1/2/3`, §6.6.1) and a module ownership table with mutual review (§4.1). Added
the team constraint that both members must be able to explain every module, and budgeted it
explicitly as 8.75 person-hours of joint walkthroughs rather than assuming it was free. Restated
the honest total as 77.00 person-hours (≈38.5 h each), up from the 66.25 h approved in v2.1, with
a full reconciliation showing that the entire increase traces to the two decisions made in this
round. Recorded two line-budget caps as still exceeded (backend outside core 515 vs 400; frontend
M1+M2 670 vs 600) and deferred both to the gates where measured numbers will exist, rather than
re-basing the caps onto the actuals. Updated the verification report (§17) so traceability, the
scenario table and the budget check reflect v2.2. `docs/HLD.md` v2.2 is now marked APPROVED AND
FROZEN. No code was written in this phase.

---

**Date:** 2026-10-08
**Phase:** 1 — Scaffold and GitHub repository (M1 only)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/__init__.py`, `backend/src/core/__init__.py`,
`backend/src/api/__init__.py`, `backend/tests/__init__.py`, `backend/tests/test_smoke.py`,
`pytest.ini`, `requirements.txt`, `.gitignore`, `.gitattributes`, `LICENSE`, `README.md`,
`.github/workflows/ci.yml`, `frontend/.env.example`, and `.gitkeep` placeholders in `data/`,
`scripts/`, `docs/report/`, `docs/pilot/`, `docs/experiments/`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Created the M1 repository skeleton against the frozen design. Claude created the
directory structure and package files, wrote one smoke test that verifies the pytest path
configuration resolves and that nothing under `src/core` imports a web framework (checked in a
clean subprocess so pytest's own imports cannot mask a violation), pinned `requirements.txt` to
the dependency versions actually installed and verified in this session rather than guessed,
configured a GitHub Actions workflow running pytest on push, wrote the MIT license and a README
stub, and initialised the git repository. Claude then created the public GitHub repository via
`gh repo create` under the student's already-authenticated account (no credentials were handled),
added a description and ten topics, and pushed two commits. After the first CI run passed, Claude
pinned the runner to `ubuntu-24.04` and upgraded the two actions to clear a Node 20 deprecation
warning, because the `ubuntu-latest` label is scheduled to migrate to Ubuntu 26 on 2026-10-19,
mid-project. Repository: https://github.com/ujwal2311/proofpilot — CI green on both commits.
No logic was implemented in this phase.

---

**Date:** 2026-10-08
**Phase:** 1 — Independent audit and pre-approved fixes
**Tool:** Claude Code (Opus 5)
**Files created:** `requirements-dev.txt`, `pyproject.toml`, `docs/READING_GUIDE.md`.
**Files modified:** `.github/workflows/ci.yml`, `requirements.txt`, `pytest.ini`,
`.gitattributes`, `README.md`, `docs/HLD.md` (v2.2 to v2.3), `CLAUDE.md`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The student commissioned an independent audit of the Phase 1 scaffold, requiring
every verdict to be backed by command output rather than by the previous session's claims, plus
ten pre-approved fixes. Claude cloned the published repository into a temporary directory and
reproduced the build from scratch (fresh virtual environment, pinned install, pytest from both
the repository root and `backend/`), identified the interpreter that created the original
environment, proved the smoke test can actually fail by temporarily adding a web-framework import
to a core module and then reverting it, scanned the full git history for credential patterns,
and verified line endings, tracked files, commit authorship and CI status.

**Correction (made in the following session, after further checks).** This entry originally
claimed the machine had no Anaconda installation and that the audit brief's premise was wrong.
That claim was itself wrong and is withdrawn. A conda (base) environment was visible in an
earlier terminal; it had been deactivated, so it was not detectable from the audit shell —
`CONDA_PREFIX` was empty, and `py -0p` and `where python` list only launcher-registered and
PATH interpreters. Direct filesystem checks confirm **Miniconda3 is installed at
`%USERPROFILE%\miniconda3`, carrying Python 3.13.11** — matching the version the student
recalled. It is not on `PATH` and `conda` is not callable from a normal shell, which is why the
audit shell could not see it. The README now instructs `py -3.12`, which selects the launcher-
registered interpreter and is therefore independent of whether conda is active.

The ten fixes were then applied as separate commits: a CI matrix across two pinned runner images
and two Python versions plus a determinism job running the suite under two fixed hash seeds and a
ruff lint job; stricter pytest configuration; a runtime/development dependency split with ruff
added; a minimal ruff configuration; expanded gitattributes rules; a rewritten and
literally-verified Windows quick-start; a reading guide that references HLD section numbers only
so it cannot drift; and a budget-only change request recorded as HLD v2.3. The Windows runner
label was confirmed against GitHub's published documentation rather than guessed, and Python 3.13
compatibility was established by resolving wheels for that target version rather than asserted.
Claude also reported gaps found beyond the fix list for the student to decide on, including an
incomplete module list in the smoke test's import guard, and did not act on them. No application
logic was written in this phase.

---

**Date:** 2026-10-08
**Phase:** 1 — Audit follow-up: decisions G1–G5 and additional fixes H1–H7
**Tool:** Claude Code (Opus 5)
**Files created:** `constraints.txt`, `CONTRIBUTING.md`, `backend/tests/test_docs_version.py`.
**Files modified:** `backend/tests/test_smoke.py`, `CLAUDE.md`, `pyproject.toml`, `.gitignore`,
`.github/workflows/ci.yml`, `README.md`, `docs/READING_GUIDE.md`, `docs/HLD.md`,
`AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm. The student supplied all twelve
decisions and fixes; Claude applied them and verified each.
**Purpose:** Replaced the core-import denylist with an allowlist that asserts every module
importing `core` pulls in is either standard library or the project's own package, and proved it
by temporarily importing `httpx` and then `yaml` into a core module and confirming each failed by
name before reverting — the allowlist also caught the transitive packages those imports dragged
in, which a denylist structurally cannot. Before making that change Claude checked the design as
instructed and confirmed `core` is not specified to load YAML; one related deviation from the
student's stated preference was found and is reported rather than changed, namely that the
architecture diagram has `core` loading `exercises.json` directly instead of receiving it from
the edge.

Made the push rule absolute and stated it in one place, after Phase 1 had pushed on an implicit
authorisation. Established `pyproject.toml` `requires-python` as the single source of truth for
the Python version and removed every restatement. Narrowed the environment-file ignore rules and
proved the behaviour with `git check-ignore` on four filenames. Added a transitive pin set and
verified every pin resolves for all four continuous-integration targets; the first verification
attempt failed and the failure was traced to the verification method rather than the pins, since
`pip download --platform` matches tags exactly and the pinned matplotlib and contourpy releases
publish different manylinux tags that no single tag satisfies. Wired constraints, cache keys and
the pip version-check setting into continuous integration. Added a test that fails when any
document cites a superseded design version, which caught a real stale reference on its first run.
Recorded in the design change log that from Phase 8 the determinism job will also diff experiment
outputs, comparing figures by hashing the plotted data rather than the image bytes. Added a
contributing guide. Corrected an earlier entry in this log that had wrongly claimed no conda
installation existed. No application logic was written in this phase.

---

**Date:** 2026-10-08
**Phase:** 1 → 2 — v2.4 change request, then `core/logic.py` (test-first)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/logic.py`, `backend/tests/test_logic.py`.
**Files modified:** `docs/HLD.md` (v2.3 → v2.4), `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Applied the approved v2.4 change request, which reverses the architecture so that no
module under `core` reads a file: the API, the command-line interface and the scripts load
`data/exercises.json` and pass dataclasses inward. This added an `Exercise` type and a loader
module to the design and closed a finding carried since the first design review, where `Exercise`
was referenced in a signature but never defined.

Then implemented the first logic module, tests before code. Claude wrote the test file, ran it to
confirm it failed for the right reason, then wrote the implementation. Because the suite passed on
the first attempt, Claude mutation-tested its own tests by introducing eight deliberate defects
into the implementation — reordering the diagnosis checks, deleting the tautology and duplicate
checks, loosening the double-cancellation rule, dropping case normalization, mis-resolving, and
swapping the missing/extra report. Seven were caught. The eighth, replacing the canonical sort
with an unsorted tuple, was not: the ordering test had been comparing two equal sets, which
iterate identically within a single process and so could never detect it. The test was rewritten
to assert the output is actually sorted and re-verified against the same defect under three
different hash seeds. This is recorded because the weakness was in work produced in this session
and was found only by deliberately attacking it. No application logic was written beyond
`logic.py`.

---

**Date:** 2026-10-08
**Phase:** 3 — `core/search.py` and `core/config.py` (test-first)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/search.py`, `backend/src/core/config.py`,
`backend/tests/test_search.py`.
**Files modified:** `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Implemented breadth-first search for the shortest resolution refutation, tests
before code, confirmed failing first. Added the search node budget as a named constant whose
value was measured rather than chosen: the slowest legal exercise-bank state needed 184 expanded
nodes and 13.9 milliseconds, and the cost per expanded node was flat at about 64 microseconds, so
the budget was set at 8,000 nodes, roughly forty times the worst measured requirement and about
half a second in the worst case. The measurement conditions are recorded alongside the constant.

One design decision departs from a literal reading of the design document and is recorded here:
exhausting the search space without finding a proof returns an error rather than the same null
value used for the node budget being reached. Those two outcomes mean opposite things to a caller
— impossible versus merely expensive — and collapsing them would have hidden the very condition
the design's short-circuit exists to prevent.

The test suite was then attacked with nine deliberate defects injected into the implementation.
Five were caught immediately; four were not, and all four were genuine weaknesses in the tests.
Two ordering tests had rebuilt a set in a different order and compared the results, which proves
nothing because equal sets iterate identically within a single process — the same mistake made
and corrected in the previous phase, repeated here. The other two used fixtures where the
naively-first choice happened to be the correct one, so an implementation that ignored the rule
entirely still passed. New fixtures were constructed specifically to separate those cases, and
all four defects are now detected. A fifth surviving defect was investigated and found to be
undetectable for a provable reason rather than a test gap, confirmed by sampling two hundred
thousand random clause pairs; the relevant guard was kept deliberately and a test now documents
why. No work beyond `search.py` and `config.py` was carried out.

---

**Date:** 2026-10-08
**Phase:** 4a — `core/english.py`, the controlled grammar (test-first)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/english.py`, `backend/tests/test_english.py`.
**Files modified:** `backend/src/core/config.py`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Implemented the controlled-English parser, tests before code. Three tests failed on
the first run and investigation showed the tests were wrong, not the implementation: they had
assumed the parser strips a negation from inside a fact phrase, when the grammar only treats a
negation as structural if it begins the clause. Everything else belongs to the fact layer. The
tests were corrected and a further test added that pins the boundary between the two layers,
since getting it backwards would have corrupted every downstream stage.

Thirteen deliberate defects were then injected into the implementation. Twelve were caught.
The survivor removed the rule that "either" forces a disjunction, and tracing why it survived
exposed a genuine hole: the existing ambiguity test only covered sentences mixing both
connectives, which a weaker rule still rejects. The uncovered case is a sentence such as
"Either it rains and it is cold", which has only one connective present and would therefore have
been parsed silently as a conjunction — the exact opposite of what the word "either" promises,
and undetectable anywhere downstream. Tests were added for that case and for its counterpart
with "both". While tracing it, a second genuine defect was found: the grammar requires at least
one connective after "either" or "both", but the implementation accepted "Either it rains" and
quietly demoted it to a plain clause. That is now refused. Both fixes were re-verified by
re-running the mutations.

The module came in at 245 lines against a 180-line estimate, and the cumulative core total is
now 582 of 975 with six modules still to build. Projecting the overrun observed so far puts the
finished core at roughly 1,091 lines, about 116 over the agreed cap. This is reported at the gate
as a budget breach requiring a decision rather than absorbed quietly. No work beyond
`english.py` was carried out.

---

**Date:** 2026-10-08
**Phase:** 4a gate — budget metric change, grammar robustness fixes, mutation record
**Tool:** Claude Code (Opus 5)
**Files created:** `scripts/loc.py`, `backend/tests/test_english_robustness.py`,
`docs/experiments/mutation_log.md`.
**Files modified:** `docs/HLD.md` (v2.4 → v2.5), `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md`, `.github/workflows/ci.yml`, `backend/src/core/english.py`,
`backend/tests/test_english.py`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The student decided that line budgets should count code lines only, excluding
blank lines, comments and docstrings, on the grounds that the caps bound logic complexity while
the comments the rules require improve explainability and should not be penalised. A measuring
script was written for this using the standard library's tokenizer rather than pattern matching,
because a pattern cannot reliably tell a documentation string from an ordinary string that
happens to begin a line. Under the new metric the breach reported at the previous gate
disappears, and the projection for the finished core sits comfortably inside the cap.

A traceability check was then run on the previous gate's corrected tests, to confirm the design
justified them rather than the reverse. The design was not silent: it already stated that only a
negation at the start of a clause is structural. However, the verification table contained a row
that attributed an example to the wrong layer, which a reader following it would have implemented
incorrectly. The row was split and the rule restated.

Four genuine defects were then found, each by a test written before the fix: quantified words such
as "someone" were accepted as ordinary facts because matching is word-based and the listed forms
did not include the compound ones; typographic characters were not folded to plain ASCII, so a
curly apostrophe could destroy a negation before the fact layer ever saw it; sentence splitting
broke decimal numbers and abbreviations; and a regression introduced in the previous gate rejected
a perfectly ordinary sentence beginning with "both". A seeded generator was also added that builds
three hundred random sentences inside the grammar, writes them out as English, reads them back and
requires an exact match.

Finally the full mutation record was written up as reportable evidence. Of thirty-four deliberate
defects injected across the three modules built so far, all thirty-four are now detected; one
further defect was shown by sampling to be undetectable for a provable reason rather than a gap in
the tests. Two defects that initially survived turned out to mark redundant code rather than
missing tests, and that code was deleted. No work beyond the grammar module was carried out.

---

**Date:** 2026-10-08
**Phase:** 4b — `core/facts.py`, fact identity and merges (test-first)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/facts.py`, `backend/tests/test_facts.py`,
`backend/tests/test_loc.py`.
**Files modified:** `docs/HLD.md` (v2.5 → v2.6), `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md`, `backend/src/core/english.py`, `backend/src/core/config.py`,
`scripts/loc.py`, `backend/tests/test_english_robustness.py`,
`docs/experiments/mutation_log.md`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The student approved five design amendments before any code was written: automatic
merges must keep every original phrase so the student can see and undo them; the word-reduction
rules must apply to every word unconditionally and repeat until nothing changes, so that a base
form and an inflected form follow the same path; the limit on how many facts a paragraph may
contain is checked only after the student has had a chance to merge; a one-word fragment produced
by sentence splitting is refused rather than turned into a fact; and hyphenated words count as one
word so that a hyphen can never be mistaken for a negation.

The word-reduction rules were prototyped and verified before being written into the design, over
thirty-six base and inflected pairs: all thirty-six reach the same key, none violates the
repeat-until-stable property, and the three collisions the design knowingly accepts all occur as
expected. Those collisions are safe only because of the first amendment, which keeps both phrases
visible to the student.

Three tests failed on the first run, each for a different reason, and one was a genuine defect:
the code sorted the two phrases in a merge before applying the relation, which meant that when the
student declared one phrase the opposite of another, the wrong one was flipped. Sorting is correct
for deciding whether two merge instructions conflict, since the pair is unordered there, but wrong
for applying a directional relation. The two are now separated.

Twenty deliberate defects were then injected into the new module. Seventeen of nineteen scored
were caught. One survivor was a rule that could never change an outcome, since an earlier rule
already produced the same result, and it was deleted. The other was a real gap: no test used a
word short enough for the minimum-length guard to matter, and without that guard short words are
reduced away to nothing and would all share one key. A test was added and both are now detected.

Separately, writing tests for the line-counting script found a defect in it: a blank line inside a
documentation block was counted twice and subtracted twice, which undercounted code and quietly
made the budget more generous than intended. Every line is now classified exactly once.

---

**Date:** 2026-10-08
**Phase:** 4b gate — identity, naming and reset-rule amendments (HLD v2.7)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/tests/test_core_layout.py`, `backend/tests/test_bank_guard.py`.
**Files modified:** `docs/HLD.md` (v2.6 → v2.7), `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md`, `backend/src/core/facts.py`, `backend/tests/test_facts.py`,
`AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Seven pre-push amendments the student approved. Phrases now carry stable
identifiers and every merge instruction names those identifiers rather than quoting the
student's words back, because quoted text stops matching the moment a sentence is edited and two
sentences can produce the same phrase. The planned shared-types module was renamed before it was
ever written, because its intended name would have shadowed a standard-library module and been
imported in preference to it; a structural test now refuses any core module whose name clashes,
not only that one. A rule was recorded stating that changing a merge after the facts have been
confirmed discards the translation and proof progress for that question, because the symbols are
reassigned from scratch and a proof built on the old assignment is no longer about the same
propositions. The reasoning behind the function-word list was written down in one place,
including why the dummy subject in "it rains" is dropped while personal pronouns are not — the
former refers to nothing, the latter refer to entities, and resolving those is out of scope.

Two tests were added for cases the previous gate had not covered: a phrase that is already
negative being declared the opposite of another, checked in both orders, since the two sign
sources must combine rather than one overwriting the other; and a conclusion naming a fact that
appears in no premise, which is reported as a warning rather than an error because it is also
exactly what a conclusion that genuinely does not follow looks like.

Finally a guard was written for the exercise bank, ahead of the bank existing. The word-reduction
rules knowingly over-merge a few word pairs, which is acceptable for a paragraph the student
wrote because they can see and undo it, but not for an exercise we ship: every student would hit
the same confusing screen and the proof would depend on them undoing it. The guard fails any
exercise containing two distinct phrases that reduce to the same key unless the author has
declared that collision, and it is itself tested against a deliberately broken fixture so there
is evidence it can fail.

---

**Date:** 2026-10-08
**Phase:** 4c — `core/cnf.py`, formula to clause form (test-first)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/cnf.py`, `backend/tests/test_cnf.py`.
**Files modified:** `docs/experiments/mutation_log.md`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Implemented the textbook three-step conversion from a parsed sentence to clause
form, tests before code. Negating the conclusion was placed in this module rather than the
entailment module, because it is the same three steps applied to a different input, whereas the
entailment module's job is truth tables rather than rewriting formulas. The module is kept
ignorant of facts and symbols: the caller supplies a mapping from phrase to literal, so polarity
and symbol assignment remain the fact module's business.

The central test is a property rather than a table: three hundred randomly generated formulas are
converted and then compared against the original on every possible assignment of truth values,
in both the plain and the negated direction. That checks the conversion preserves meaning, not
merely satisfiability, which matters because both the student's proof and the entailment verdict
are computed from these clauses.

A process failure occurred during mutation testing and is recorded because it was avoidable. One
injected defect sent the conversion into unbounded recursion; the shell loop driving the run timed
out partway through and left the file in its mutated state, and because the module had not yet
been committed there was no copy to restore from. The file was repaired by hand, committed
immediately, and the driver rewritten so that each mutant runs with its own time limit and the
file is restored from version control in all cases, including failure. Committing before
mutation work is now the practice.

Fifteen defects were injected. Twelve of fourteen were caught on the first pass. One survivor was
redundant code, which was deleted: the helper that flattens nested groupings can never encounter
one, because the distribution step already flattens as it rebuilds. The other two were genuine
test gaps: ordering was being asserted on a result small enough to come out ordered by chance, and
a normalisation step that unwraps a single-item group was never exercised because the parser
cannot produce one. Both are now covered, and all fifteen are detected.

---

**Date:** 2026-10-09
**Phase:** 5 — `core/entail.py` and `core/relevance.py` (test-first), plus the 4c gate work
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/entail.py`, `backend/src/core/relevance.py`,
`backend/tests/test_entail.py`, `backend/tests/test_relevance.py`,
`backend/tests/test_differential.py`, `scripts/mutate.py`, `data/mutants.json`,
`docs/experiments/differential.md`.
**Files modified:** `docs/HLD.md` (v2.7 → v2.8), `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md`, `backend/src/core/english.py`,
`docs/experiments/mutation_log.md`, `AI_USAGE_LOG.md`.
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Built the two modules that decide whether a conclusion follows and which premises it
can reach. Entailment is settled by examining every possible assignment of truth values rather
than by searching for a proof, which is what allows the proof search to be skipped entirely when
the answer is already known. The counterexample shown to a student is the first qualifying row in
a fixed order, so the same argument produces the same explanation on any machine. The relevance
filter refuses to run on contradictory premises rather than trusting the caller to have checked,
because its correctness argument depends on that check and a contradiction hiding in the
discarded part would destroy the only proof.

The most valuable new tests compare the two methods against each other rather than against the
author's own expectations. Seven hundred and sixty randomly generated arguments were decided both
by the truth table and by saturating under the resolution rule, and the two agreed every time.
The resolution side is written inside the test rather than reusing the search module, partly
because the search answers a harder question and did not finish in reasonable time on random
input — the first attempt had to be abandoned — and partly because sharing no code makes the
comparison worth something. A second differential test confirms that filtering the premises never
changes the verdict.

The mutation driver and its definitions were committed so that every number in the mutation log
can be regenerated with one command, and the conventions that affect the score were written down:
a timeout counts as detected, and a defect whose anchor text no longer exists is reported as
retired rather than silently skipped. Run against the committed code, all forty-eight existing
defects were detected.

A second process failure is recorded. The driver restored each file using version control, which
silently does nothing for a file that has not yet been committed; both new modules were in that
state, so two files were left holding injected defects. This is the same outcome as the failure
in the previous phase, from a different cause. The driver now keeps its own copy of the original
and verifies the file matches before continuing, which has no such precondition.

Of eighteen deliberate defects injected into the new modules, sixteen were caught immediately.
Both survivors were the same weakness wearing two hats: a property was being asserted on an
example too small to distinguish right from wrong — one satisfying row, where first and last
coincide, and three symbols that happened to come out in order. Both tests were widened and all
eighteen are now detected.

---

**Date:** 2026-10-10
**Phase:** 5 gate addendum — mutation isolation, search termination, differential gaps, budget
reconciliation (items A1–A6 of the student's gate instruction)
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/tests/test_mutation_driver.py`, `backend/tests/test_search_budget.py`,
`docs/experiments/search_latency.md`
**Files modified:** `scripts/mutate.py`, `data/mutants.json`, `backend/src/core/search.py`,
`backend/src/core/config.py`, `backend/tests/test_differential.py`, `docs/HLD.md` (v2.8 → v2.9),
`docs/experiments/mutation_log.md`, `docs/experiments/differential.md`, `CLAUDE.md`, `README.md`,
`docs/READING_GUIDE.md` (version references only)
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Six items the student set as blocking before the Phase 5 push.

The incident from the previous phase was verified rather than assumed closed. A surviving mutant
passes the tests by definition, so a green suite says nothing about whether a file is still
holding an injected defect; every one of the sixty-six definitions was therefore checked directly
against the committed blob for the presence of its anchor and the absence of its replacement. All
sixty-six anchors were present and the committed content matched the working tree. Nine
replacements did appear, and each was traced to a specific line and shown to be a prefix of its
own anchor, ordinary Python occurring elsewhere, or in one case the English word "pass" inside a
docstring. The committed source carried no mutation.

The driver was then rebuilt rather than patched again, because it had now failed three times in
the same way from three different causes. Mutations are applied only inside a detached worktree at
the committed revision, so the real source is never opened for writing; the run refuses to start
on a dirty tree or an untracked target, which was the precondition that failed last time; and the
source tree is fingerprinted before and after, aborting on any difference. A test asserts each of
those properties, including that a write inside the isolated copy leaves the real source
byte-identical. The refusals are tested against a throwaway repository, since dirtying the real
one to test the check would be the bug the check exists to prevent.

The search hang was reproduced under a hard subprocess timeout and measured rather than guessed
at. The node cap bounded the wrong quantity twice over: successor generation was never charged, so
a search at its nominal eight-thousand-node cap had generated a hundred and eighty-four thousand
states and was holding a frontier of forty-six thousand; and the hint function opened a fresh
full-budget search for every candidate step, which took twelve point seven seconds for a single
hint on an input inside the documented limits. The cap is now a budget counted in generated
states, charged one at a time, and shared by one public call. Cost was then measured per proof
depth and grows about sevenfold per step, which is a property of searching over clause sets rather
than of the budget, so the value was chosen to cover the deepest proof the exercise bank can
contain with roughly fifty-seven times headroom, and the point at which own questions fall back to
the rule-based hint is written down as a limitation with a test behind it. Latency figures are
recorded as goals for one named machine, never as claims, and the automated assertion is a
deliberately loose ceiling whose job is to catch a regression of orders of magnitude.

Two gaps in the differential tests were closed. The first test used to skip contradictory premises,
which exempted the branch the pipeline leans on hardest; it now asserts the stronger claim in both
directions, that resolution derives the empty clause from the premises alone exactly when the truth
table finds no model for them. The second only ever measured the filter's willingness to discard,
because its generator always contained a disconnected component; a third generator builds
fully-connected shuffled chains where nothing may be dropped, and the shuffle is what makes
transitivity load-bearing rather than incidental.

Two of the new tests were rewritten after the mutants showed them to be worthless. Asserting that
a budget had not been overdrawn passes for an implementation that funds each probe separately,
because such an implementation leaves the shared counter almost untouched and so looks thrifty.
Both tests now grant exactly the opening search's cost plus one unit, which makes the two
behaviours give opposite answers.

The line-budget arithmetic was redone and does not come out in the project's favour. The built
modules measure ninety lines under their own estimates, but the core cap was lowered from
nine hundred and seventy-five to a six hundred and fifty target and a seven hundred ceiling across
two earlier change requests without the bottom-up estimate ever being re-derived against it, and
three of the design document's budget tables were still printing the superseded figures. The
projection is about eight hundred against the ceiling, the figure of six hundred and ninety-seven
quoted in the previous change log is not derivable from the table it cites, and the same problem
affects the API, scripts and frontend buckets. The arithmetic, the plan, and three options are
recorded for the student's decision; no cap has been moved and no tutoring module was written.

---

**Date:** 2026-10-11
**Phase:** HLD v2.10 (budget decision, bounded cache) + Phase 6a (`models.py`, `bkt.py`)
**Tool:** Claude Code (Opus 5)
**Files created:** `budgets.toml`, `backend/src/core/models.py`, `backend/src/core/bkt.py`,
`data/policy.yaml`, `backend/tests/test_models.py`, `backend/tests/test_bkt.py`,
`backend/tests/test_policy.py`
**Files moved:** `scripts/loc.py` → `tools/loc.py`, `scripts/mutate.py` → `tools/mutate.py`
**Files modified:** `backend/src/core/config.py`, `backend/src/core/search.py`,
`backend/tests/test_search_budget.py`, `backend/tests/test_loc.py`,
`backend/tests/test_docs_version.py`, `backend/tests/test_mutation_driver.py`,
`data/mutants.json`, `docs/HLD.md` (v2.9 → v2.10), `docs/experiments/mutation_log.md`,
`CLAUDE.md`, `README.md`, `docs/READING_GUIDE.md`, `.github/workflows/ci.yml`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The student's budget decision, one new defect fix, and the first half of Phase 6.

The budget decision was option (c) with six conditions, and all six were applied. Two of the
proposed simplifications were rejected by the student with reasons that are now recorded in the
decisions table: the session state stays in the logic layer because the command-line interface
drives that layer directly and would otherwise have to go through the web layer to play an
exercise, and the stage-and-action transition table stays in code because transitions decide what
may happen next and raise named errors, which is behaviour a reader should see rather than look up
in a data file. The evidence mapping did move to a data file, since it is a pure lookup with no
control flow in it. The mastery history was cut from the first milestone because it only ever fed
a stretch feature, and the model needs the current probability rather than the sequence that
produced it.

Two of the conditions were about the budgets themselves rather than the code. Development tooling
moved out of the capped bucket, because capping it had been penalising exactly the work that makes
the other caps trustworthy — hardening the mutation driver after three incidents cost forty-five
lines of a bucket that also had to hold the evaluation scripts. And every cap now lives in one
file read by the measuring tool, with the figures removed from the design document, the rules file
and the README, because three separate tables had each kept their own copy and all three had
drifted; a test now fails the build if a cap number reappears in prose. All four buckets were
re-derived from the measured actuals plus a per-module estimate and frozen, with the ceiling set
ten percent above the estimate and the overrun rule written down: an overrun cuts second-milestone
scope first, and the caps are not raised again.

The memoised distance table was unbounded, which matters because the server is long running. It
was measured rather than reasoned about: two hundred distinct requests grew it to one thousand and
sixty-two entries, about five per request, growing linearly and without limit, at roughly one and
two thirds kilobytes retained per entry. A single request only ever confirms two distances, so a
bounded table never evicts anything during a request and every useful hit still lands. Eviction
can cost a cached answer but a test proves it can never change one.

The first half of Phase 6 was written tests-first, and the tests found a defect in the learning
model before any deliberate mutation did. A test was written to assert the obvious — that the
probability of mastery stays strictly between zero and one — and it failed. The model never
reaches one, but floating-point arithmetic does: twenty-three consecutive correct answers drive it
to exactly one, and from there the formula for a wrong answer returns one again, so the skill
freezes permanently and the tutor would have kept asserting mastery that every later wrong answer
contradicted. The value is now held just inside the interval, which leaves about ten wrong answers
to bring a mastered skill back below the threshold and is far too small to change any displayed
number.

Three of the new tests were themselves wrong and were corrected rather than relaxed, which is
worth recording because each would have passed for broken code. One checked that the data module
reads no file by searching its text for the word used by the file format, and flagged its own
explanatory comment; it now examines the parsed syntax tree instead. One asserted a total number
of combinations that had been miscounted. One checked that nothing depends on the practice or
own-question mode by searching for the word "mode" and matched the comment explaining that very
property; it now checks the structure of the table.

Of the twelve deliberate defects injected into the two new modules, all twelve were detected on
the first run, and the whole set of eighty-two across nine modules was detected on the committed
code with the source fingerprint unchanged.

---

**Date:** 2026-10-12
**Phase:** Full-scope sprint to the `progress-v1` tag — standing approval recorded, block B0
**Tool:** Claude Code (Opus 5)
**Files modified:** `budgets.toml`, `tools/loc.py`, `backend/tests/test_loc.py`,
`docs/HLD.md` (v2.10 → v2.11), `CLAUDE.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Record the standing approval the student granted for the sprint, and run the budget
check that opens it.

The student granted a standing approval for the sprint ahead of the progress review: within a
sprint block, Claude may commit and push without waiting for a per-gate approval, but only if the
whole test suite passes under both hash seeds, the formatter and linter are clean, the line
budgets hold, the version and consistency checks pass, the frontend builds once it exists, and
continuous integration is green after the push. The approval narrows the publishing rule and
nothing else; it is written into the project rules as a clearly marked temporary section that is
deleted at the tag, and it names the five conditions that still require stopping to ask. Every
academic-integrity rule is unchanged, in particular that no report prose is written here, that the
held-out paragraphs and the pilot data are written only by the team, and that no reference enters
the bibliography without its publisher page having been fetched.

The budget check that opens the sprint asked whether the frozen core derivation covered the
second-milestone modules. It did not, and the gap was wider than the question assumed: the
translation module had been priced as a single line item deliberately placed outside the cap, the
narration module had never been priced at all despite being named in the scope list since the
first revision, and the typed-formula parser had been priced as a piece of the user interface
rather than as the core module it has to be. The second milestone therefore had a scope but no
budget, and the only two ways to build it were to raise a frozen cap, which the overrun policy
forbids, or to let its overrun be charged against the first milestone. It now has its own bucket,
derived module by module before any of the code exists, with the ceiling set ten percent above the
estimate as everywhere else, and the first-milestone cap untouched. The two buckets share one
directory, so the measuring tool learned to exclude files by name and a new test fails the build
if any core module is owned by both buckets or by neither — which is the one failure an exclude
list makes possible and the one that would go unnoticed.

---

**Date:** 2026-10-12
**Phase:** Sprint block S1 — the three fixes the student set at the Phase 6a gate
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/loader.py`, `backend/tests/test_loader.py`
**Files modified:** `backend/src/core/config.py`, `backend/src/core/bkt.py`,
`backend/tests/test_bkt.py`, `backend/tests/test_models.py`, `backend/tests/test_loc.py`,
`data/mutants.json`, `budgets.toml`, `docs/HLD.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Three fixes, each of which replaced a value or a promise with something derived.

The ceiling on the probability of mastery had been introduced as a guard against floating-point
arithmetic, and the recovery length it implied — about ten consecutive wrong answers before a
mastered skill is lost — was a side effect that nobody had chosen. The student replaced it with a
teaching rule: one or two wrong answers from a student who has mastered a skill are slips and must
not revoke it, and a third consecutive wrong answer must. That rule is a condition on the ceiling,
and bisecting the exact update showed it admits only a narrow window: set any higher and the
second wrong answer already revokes mastery, any lower and the third one still does not. One power
of ten lies inside the window, and it is now the value, with the window re-derived from the shipped
formulas by a test so that changing a learning parameter or the threshold fails the build rather
than quietly lengthening recovery.

The lossless round trip of the session state belongs to the block that builds the web layer, since
that is where the conversion will live. What was added now is the structural precondition that
makes such a round trip possible at all, because that is a property of the data model and one new
field can break it: every field is checked against a recursive notion of what can be written as
JSON, with the key rule deliberately stricter than the value rule, since an object key must be a
string while a pair is a perfectly good value. The first version collapsed the two rules into one
and accepted a mapping keyed by pairs. A companion test shows the check rejecting a set, a frozen
set and a badly keyed mapping, all of which are natural things to reach for in a codebase where a
clause is itself a frozen set.

The evidence table is indexed with no default and no fallback, deliberately, because a default
would score a skill the student's action never tested. The cost of that choice is that an
incomplete table is a crash in front of a student, mid-session, on whichever trigger happens to be
missing. It is now validated once at startup by the edge loader against the enumeration of what a
step can actually produce, with a named error for every failure mode and a deliberately broken
fixture file for each one. The rule about which triggers are evidence is checked in both
directions, since a scoring row that observes nothing is a dead feedback path and a non-evidence
row that starts scoring would punish a student for being refused by the grammar rather than for
being wrong.

Writing that loader exposed an unrelated gap: the bucket meant to measure it matched the command
line interface by name, so the one module that reads a data file was in no budget at all. The
pattern now covers the whole directory, and the check that every core module belongs to exactly
one bucket was generalised to every measured tree in both directions. The same gap leaves a risk
that is recorded rather than acted on: the frozen estimate for that bucket allowed ten lines for
loading the policy and no line item for the loader itself, and the validator alone is larger than
that. The projection is checked against the ceiling before the web layer is written, and crossing
it stops for a decision rather than being absorbed.

---

**Date:** 2026-10-12
**Phase:** Sprint block S2 — the tutoring policy module, and the split that paid for it
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/core/tutor.py`, `backend/src/core/session.py`,
`backend/tests/test_tutor.py`
**Files modified:** `backend/src/core/english.py`, `backend/tests/test_core_layout.py`,
`backend/tests/test_loc.py`, `backend/tests/test_docs_version.py`, `tools/loc.py`,
`budgets.toml`, `data/mutants.json`, `docs/HLD.md`, `docs/READING_GUIDE.md`, `CLAUDE.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Build the module that decides what a student's action means, and resolve the budget
overrun that writing it exposed.

The module came in at more than twice its estimate, which took the core tree past the ceiling that
fails the build, so the block stopped and the student decided. Measuring it function by function
showed the estimate had been accurate about everything it covered; what broke the budget was that
the mandatory pipeline ordering — a named correctness requirement with its own test — belonged to
no module in the design document and to no line item in the budget file. That is the third
omission of the same shape in two days, after the second milestone's modules and the data loader,
and in every case the estimate had left something out rather than the code having grown.

The student chose to split the module in two, for the design reason rather than the budget one.
One half is policy: what an action means, what may happen next, what a hint may reveal, which
exercise comes next — all pure functions over plain values, none of which need a session to be
tested. The other half is mechanics: the reading pipeline, and every edit to the session. The
consequence worth having is that the session is now written by exactly one module, where before
the module deciding policy also edited the session and a change to either could reach the other
with nothing to say so. That boundary is enforced by a test that parses every core module and
fails if any but the one owner constructs or copies a session, with a companion test proving the
check is not vacuous.

The student attached conditions, all of which are in place. The measuring tool and every budget
table now print a combined core total beside the three separate buckets, so a split made for sound
reasons cannot present one cost as three small ones. No further bucket may be added: a later
overrun stops for a decision, and the bucket list is asserted so adding one fails the build. The
design document records the decision as a conscious, one-time choice to exceed the frozen core
budget in order to keep the full scope for the progress review, with the measured numbers and with
the admission that the tree now needs a fifth more than the frozen figure allowed. The new module
was added to the design document, the reading guide, the per-module explanation list and the
mutation targets.

Two findings came out of the work itself. The conclusion had been parsed without going through the
sentence splitter that normalises the paragraph, so its trailing full stop stayed attached and the
worked example in the design review stopped following from its own premises — a wrong answer rather
than a crash, and the kind that a suite of unit tests on separate modules cannot see. And the test
that guards against a budget figure being restated in prose had to be narrowed: a two-digit figure
cannot be told apart from an ordinary number, and the new bucket's figure collided with three
unrelated numbers in the design document. Rather than exempt whole sections, measurement records
are now fenced explicitly and dated, the guard covers only figures of three digits or more, and
the gap this leaves is stated in the test rather than left to be discovered.

---

**Date:** 2026-10-12
**Phase:** Sprint block S3 — the exercise bank, the command-line gate, and the shared edge
**Tool:** Claude Code (Opus 5)
**Files created:** `data/exercises.json` (AI-DRAFTED, PENDING HUMAN REVIEW), `data/messages.yaml`,
`data/difficulty.json` (generated), `scripts/difficulty.py`, `backend/src/cli.py`,
`backend/src/app/__init__.py`, `backend/src/app/render.py`, `backend/src/app/view.py`,
`backend/tests/test_bank.py`, `backend/tests/test_cli.py`, `backend/tests/test_adapters.py`,
`backend/tests/test_normalisation.py`, `docs/experiments/cli_transcript.md`
**Files moved:** `backend/src/loader.py` → `backend/src/app/data.py`
**Files modified:** `backend/src/core/english.py`, `backend/src/core/config.py`, `budgets.toml`,
`.github/workflows/ci.yml`, `docs/HLD.md`, `docs/READING_GUIDE.md`, `data/mutants.json`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The twelve practice exercises, the command-line gate that proves the tutor needs no
web layer, and the restructuring the student directed when the line budget came under pressure.

THE EXERCISES ARE DRAFTED HERE AND AWAIT HUMAN REVIEW. They are listed as such because they are
content a student reads, not code: the team should read all twelve before the review and change
anything that reads badly or teaches the wrong habit. What is already checked mechanically is that
each one parses, that the entailment the author claimed for it is the entailment the truth table
computes, that it stays inside the clause bound the latency measurements assume, and that it does
not depend on a student noticing and undoing a merge the stemmer made. Between them they cover
every connective the grammar supports, three long paragraphs with irrelevant premises, two
conclusions that do not follow, and a spread of punctuation and capitalisation so that the bank
itself exercises the text normalisation.

Difficulty is computed from the shortest proof and written to a separate file, never stored beside
the exercise, and a continuous-integration step regenerates it and fails if the committed version
would change. A hand-written difficulty would survive an edit to a paragraph and to the search
itself, and every number downstream would inherit it.

Two findings came from running the bank through the real pipeline rather than reasoning about it.
The merge guard, written months earlier against fixtures, reported five collisions on the real
exercises that were all false alarms: a phrase and its own negation share a canonical key by
design, because the key is computed after the negation is stripped, and they correctly become one
proposition with opposite signs. Made aware of polarity the guard reported nothing at all, which
would have left it passing vacuously — so one exercise now carries a genuine same-polarity merge
that the author declares, and the guard is checked in both directions: an undeclared merge fails,
and so does a declared merge the stemmer no longer makes.

The student then directed a restructuring, on finding that the line budget for everything outside
the logic was under pressure. Everything both clients need now lives in one shared edge: loading
and validating the data files, the single text-preparation entry point, turning a code into the
words a student reads, and owning the board's clause names. The command line and the web layer
became input and output only. All user-facing wording moved into one reviewable file, and a test
parses both adapters and fails on any string that reads like a sentence, because that kind of
duplication returns one convenient line at a time rather than by decision.

The startup validation of that wording file found two real mistakes on its first run, which is the
best argument for having written it. One template used a placeholder the renderer never supplies,
which would have been a crash in front of a student. In the other direction, the renderer supplied
the offending phrase to the warning about a conclusion mentioning something no premise does, and
no template used it — so the student was told that something was missing without being told what.

---

**Date:** 2026-10-12
**Phase:** Sprint re-baseline — the root cause of four overruns, and the two recorded raises
**Tool:** Claude Code (Opus 5)
**Files modified:** `budgets.toml`, `backend/src/app/data.py`, `backend/src/core/config.py`,
`backend/tests/test_data.py`, `backend/tests/test_smoke.py`, `backend/tests/test_docs_version.py`,
`scripts/difficulty.py`, `docs/HLD.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Find out why four sprint blocks in a row ran past a line budget, and fix the method
rather than the numbers.

The student decided to record two one-time ceiling raises rather than cut scope or weaken checks,
and required that they be called what they are. They also asked for the root cause, because four
of the same surprise in two days is a pattern rather than bad luck.

The cause is a single one. Every line estimate in the design document was produced by listing the
named modules in its ownership table and costing each of those. Anything that lives between named
modules — loading a file, validating it, enforcing the order the pipeline must run in, turning a
code into words, naming the clauses on screen, persisting a session, wiring one layer to another —
was costed at nothing, because the method never went looking for it. The modules themselves were
estimated well: the module that prompted the first stop came in within one line of its figure, and
the two still to be written are now projected under theirs. The method was not wrong about
modules. It was wrong about glue, and glue is about a third of the system.

So the fix is a single re-derivation covering everything still to build, in which every bucket
lists its glue items explicitly beside its named modules: the browser's data-fetching wrapper, its
local-storage guard and its state hook; the shared helper that stamps every results table with the
commit it was generated at; rebuilding a proof board from a stored session; and the one function
that constructs a session, which has to live in the module that is the only permitted writer of
one. Ceilings stay ten percent above the estimates, no bucket is added, and after this no budget
interrupts the sprint unless a bucket passes its re-baselined ceiling.

The structural validation of the three data files was also rewritten as declarative models, with
the semantic checks left as explicit code because each is a cross-check against an enumeration
elsewhere in the system and that argument has to be readable. Honest outcome: the module grew by
ten lines rather than shrinking. What it bought is a stricter check for less reading — an unknown
key is now refused rather than ignored, which means a mistyped section name is reported where it
occurs instead of surfacing later as a missing row, and a hand-written difficulty can no longer be
placed in the exercise file at all rather than merely being unread. The same models are what the
web layer will validate requests with, so the cost moves rather than repeating.

One more gap closed on the way. The guard that keeps third-party packages out of the pure logic
imported only the package, whose initialiser imports none of its modules — so it would not have
noticed a validation library imported inside one of them. It now imports every module in a clean
subprocess, and the fix was verified by injecting such an import and watching the test fail.

---

**Date:** 2026-10-12
**Phase:** Sprint budget policy change — line caps become reported, two gates replace them
**Tool:** Claude Code (Opus 5)
**Files modified:** `budgets.toml`, `pyproject.toml`, `tools/loc.py`, `backend/src/core/english.py`,
`backend/src/cli.py`, `backend/tests/test_loc.py`, `.github/workflows/ci.yml`, `CLAUDE.md`,
`docs/HLD.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Stop measuring the wrong thing. Five budget stops in one sprint were all estimation
error rather than excess code, so the student made the bucket caps reported and replaced them with
two checks that measure the actual goal.

The goal the caps stood in for is that both team members must be able to explain every module in
the viva. A ceiling on the total lines in a directory is a poor proxy for that, and a proxy that
halts work five times while the thing it proxies for was never in doubt is the wrong instrument.
The two replacements measure it directly and both fail the build: a cyclomatic-complexity limit of
ten per function, and a limit of sixty code lines per function. The second counts code only, so
the explanatory comments the project rules require are never charged against it — a function of
two statements wrapped in eighty lines of explanation measures two, and a test asserts that, since
a gate that punished comments would work against the thing it exists to protect.

Switched on, the length limit found nothing: the longest function in the repository was
forty-eight lines of the sixty allowed. The complexity limit found two, and both were fixed by
extraction rather than excused. The grammar's sentence parser scored eighteen; it is now three
phases — refuse bad input, then the productions recognised by the first word, then the infix ones
— with the five first-word forms moved into a dispatch table. The order of those phases is a
correctness requirement rather than a preference, because a sentence beginning with "if" must
never be read as the infix keyword of a different production, and that ordering is now one visible
line instead of an implicit property of a long function body. All the grammar and clause-form
tests pass unchanged, which is what makes the extraction safe to believe. The command loop of the
terminal client scored eleven and became a table, which has the side benefit that its command set
can be checked against the help text at a glance.

An exemption list exists for functions that genuinely cannot be shortened, each needing a one-line
reason, and it is printed on every run so that an exemption is visible rather than buried. It is
empty.

The root cause of the fifth miss is worth separating from the four before it. Those four had no
line item at all for a whole component. This one had an item and the item was wrong by ninety per
cent, because it priced the idea of a function rather than the lines the language requires: the
session object has sixteen fields, so its constructor is sixteen lines, the keyword-only signature
is eight parameters, and the loop that names the clauses is thirteen — thirty-seven mechanical
lines before any logic at all.

---

**Date:** 2026-10-12
**Phase:** Sprint block S4 — the web layer
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/src/api/main.py`, `backend/src/api/schemas.py`,
`backend/src/app/audit.py`, `backend/tests/test_api.py`, `backend/tests/test_state_roundtrip.py`
**Files modified:** `backend/src/core/config.py`, `backend/src/core/models.py`,
`backend/src/core/session.py`, `backend/src/app/view.py`, `backend/src/cli.py`,
`backend/tests/test_adapters.py`, `backend/tests/test_dead_references.py`,
`backend/tests/test_models.py`, `backend/tests/test_tutor.py`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** The four endpoints, their schemas, their error model, and the property test that the
session survives a trip through the browser unchanged.

The session object is declared in one place and one place only. The web layer validates and
serialises the logic layer's own dataclasses rather than keeping a parallel declaration of the
same sixteen fields, which is what the earlier decision to keep the session in the pure layer
would otherwise have cost. Only the envelopes are written by hand, because what a client sends and
receives genuinely is the web layer's own business.

The round-trip test is a property over two hundred randomly shaped sessions rather than a handful
of examples, and it asserts two things. Lossless: a session that goes out and comes back is the
same session. Canonical: the same session always produces the same bytes, which matters because
lossless on its own would pass on output that varied between runs, and a client comparing two
responses would see changes that were not there. The generator is seeded so a failure can be
reproduced, and a companion test asserts that it actually varies the shape — that the empty
clause appears, that a refused sentence appears, that an undecided verdict appears — because a
property test over two hundred near-identical cases is one case run two hundred times.

Writing that test is what surfaced the real gap. A claim in a docstring about the validation
refusing to coerce types turned out to be false when measured: the library's default mode happily
turns the string three into the number three. Checking that led to noticing that the design
document's list of conditions a tampered session must be refused for had not been implemented at
all — an unknown clause name, a symbol belonging to no fact in the exercise, too many clauses,
too many literals, a mastery value outside the open interval the model is defined on. All of them
are now refused with a named code, each by its own request in the tests, and the two limits the
document names were added as constants. The point of the distinction is that none of these is a
wrong answer, so none of them is teaching content: they are transport errors rather than feedback.

Four defects in tests and tooling were found and fixed within the block, as the autonomy rule
allows. The guard that keeps wording out of the client adapters flagged three diagnostic messages
the moment they were written inside the web layer, which is exactly its job; the validation they
belong to moved into the shared edge, where it reads better anyway. The same guard's companion
check wrongly required the schema module to import the shared edge, though it makes no decisions
and has no use for it; that check is now scoped to the modules that actually drive the system. The
list of files the sprint has not yet built still named one that now exists. And the complexity
gate switched on earlier in the day caught the new validation function at eleven branches before
it was ever committed, which is the first time one of these gates has prevented rather than
reported a problem.

---

**Date:** 2026-10-12
**Phase:** Sprint block S4.1 — API hardening
**Tool:** Claude Code (Opus 5)
**Files created:** `backend/tests/test_api_hardening.py`
**Files modified:** `backend/src/api/schemas.py`, `backend/src/api/main.py`,
`backend/src/app/data.py`, `data/messages.yaml`, `backend/tests/test_api.py`,
`backend/tests/test_adapters.py`, `README.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Four hardening items the student set after accepting the web layer: strict
validation, request size limits, a single error shape, and an honest limitation in the readme.

Validation is now strict, so a string containing a digit is no longer quietly accepted where a
number belongs, nor a word where a true-or-false value belongs. Getting there required one
discovery worth recording: the strict mode of the validation library refuses a plain mapping for a
dataclass outright, demanding an actual instance, so the only route that both refuses coercion and
accepts a request body is to validate the body as text. The parsed body is therefore re-serialised
for one hop. That costs a little work per request and buys the guarantee, and the alternative
would have put the validation library inside the pure logic layer, which a test forbids.

Request bodies are limited two ways, because either alone is trivially defeated. The declared
length is checked first and refuses the honest oversized request before any of the body is read;
the bytes that actually arrive are then measured, because a client can understate that header or
omit it entirely. A test sends a body as a stream with no length header at all and confirms the
second check is the one that catches it. The paragraph and the conclusion also have their own
length limits, well above anything the grammar would accept.

Every error now returns the same three fields, including the two that were easy to leave out and
are the two a client actually trips: the framework's own rejection of a malformed body, which
happens before any endpoint runs, and an unhandled exception. The wording comes from the single
message file, so every sentence a person may read is in one reviewable place; a server error
carries no detail at all, since a stack trace in a response body tells a student nothing and leaks
paths.

Writing that handler found a real defect in it. The function that builds an error response looks
its wording up through the loaded runtime, and the runtime can be the very thing that failed —
a bad data file at startup is reported through this path. The first version caught only lookup
failures, so injecting a different kind of error produced a server error with an empty body: the
handler failed while handling, and the client received something it could not parse. The fallback
is now total, because an error path that can fail is not an error path.

Two of the test fixtures were wrong in the same instructive way, and both were corrected rather
than worked around: a paragraph built to be large tripped the sentence limit, and the second
attempt tripped the distinct-fact limit. The point they make is that the size limits can never be
what refuses an honest paragraph — the grammar's own limits bite first by a wide margin — and the
test now says so.

The readme records the limitation plainly. The session lives on the client and the client can edit
it; the server validates structure and range but not integrity, so a determined student can change
their own mastery scores. That is acceptable for a practice tool that grades nothing — the only
person they can mislead is themselves — and it would have to change before any use where the
record matters. Signing the session is named as the future work.

---

**Date:** 2026-10-12
**Phase:** Facts-stage-skip fix (spec conformance, between S4.1 and S5)
**Tool:** Claude Code (Sonnet 5)
**Files created:** none
**Files modified:** `backend/src/core/tutor.py`, `backend/src/core/session.py`,
`backend/src/api/schemas.py`, `backend/src/api/main.py`, `backend/src/app/data.py`,
`backend/src/cli.py`, `data/messages.yaml`, `backend/tests/test_tutor.py`,
`backend/tests/test_api.py`, `backend/tests/test_api_hardening.py`, `backend/tests/test_cli.py`,
`docs/HLD.md`, `docs/experiments/cli_transcript.md`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** `state_of` was putting a settled exercise straight into stage `"prove"`, skipping the
Facts confirmation screen that section 14 names as the explicit safety net for the project's
biggest known limitation — a connective inside a fact phrase mis-splitting silently. The student
found this and specified the fix end to end across all three layers; every edit was made with the
Edit tool (no scripted or sed-style replacement anywhere in this block).

The core change is one line in `session.state_of` plus a new transition: a settled exercise now
opens on `"facts"`, and only the new `confirm_facts` action (core `tutor.advance`, API discriminated
union, CLI `yes`/`confirm` command) can leave it. Any proving action sent first — `step`, `hint`,
`claim_not_provable`, `translate` — raises a new `FactsNotConfirmed`, kept as its own exception
type (not a reused `TransitionError`) because Starlette dispatches handlers by exact exception type
first via the MRO walk, so registering it separately guarantees the specific `FACTS_NOT_CONFIRMED`
code regardless of dict order, while the generic `WRONG_STAGE` still covers every other misordered
call. `confirm_facts` is named apart from Translate's `confirm` (same shape, different stage, M1 vs
M2) so the two exits are never conflated in logs or tests.

The CLI change was the largest: `Play.open` now shows the grouped facts and an entailment summary
without building the board, a new `facts_loop` accepts `yes`/`confirm`, `merge <a> <b> <rel>`, or
`quit`/`skip` until confirmed, and only then does `Play.confirm` mint the board via
`session.state_of`. Updating the existing CLI tests for this took two passes: most scripts needed
only a leading `yes` (added via a `confirmed: bool = True` default on the test `run()` helper), but
`--own` mode reads its paragraph and conclusion as the first two script lines, before the Facts
screen ever opens, so those four tests needed the confirmation placed by hand after the two
prompts, or (for the one case that is refused before reaching the Facts screen at all) removed
entirely. `docs/experiments/cli_transcript.md` was regenerated by actually running both scripted
sessions and diffing the output against the doc text, rather than hand-edited to match — per rule
10, no number or transcript line in that file is invented.

All 786 backend tests pass (787 with `PROOFPILOT_SLOW=1`), `ruff check`/`ruff format --check` are
clean, the C901 and 60-line function gates pass with an empty allowlist, and the `tutor`/`session`
mutation suites both still score 14/14 and 12/12 caught against the new code. `docs/HLD.md` §8 (the
action table and error-model table) and §17.9's scenario table were updated to document
`confirm_facts`/`FACTS_NOT_CONFIRMED` as new scenario (r) — a wording and contract update, not a
design change, since the Facts stage and its confirmation step already existed in the frozen v2.11
design; this fix makes `state_of` and the API/CLI honor what section 14 already specified.

---

**Date:** 2026-10-12
**Phase:** Sprint block S5 — the React frontend (M1), plus one core bug found verifying it
**Tool:** Claude Code (Sonnet 5)
**Files created:** `frontend/src/App.jsx`, `Explanation.jsx`, `Feedback.jsx`, `MasteryBars.jsx`,
`ProveBoard.jsx`, `ReadFacts.jsx`, `api.js`, `index.css`, `labels.js`, `main.jsx`, `storage.js`,
`useSession.js`
**Files modified:** `backend/src/core/session.py`, `backend/tests/test_tutor.py`
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Build the M1 frontend (Read & Facts, Prove, Explanation) against the already-shipped
API, and verify it end to end in a real browser rather than by test suite alone.

Most of `frontend/src/` already existed in the working tree from earlier in the sprint; this block
picked it up, found it would not build (`main.jsx` imported a `./index.css` that was never
written), and wrote the missing stylesheet — plain CSS, no framework, large type and high contrast
throughout, because a pilot student reads this off a projector, not a personal screen.

Driving the built app in an actual Chrome tab (not just `npm run build`) found two real defects
that no test had caught, because no test exercises the browser:

1. `ReadFacts`'s confirm button was wired to send a `hint` action instead of `confirm_facts` — a
   stale placeholder from before the backend grew that action. Sending it would have hit the new
   `FACTS_NOT_CONFIRMED` refusal from this session's earlier fix, on literally the first click.
   Caught only because the fix was tested in a browser rather than trusted from the API test suite.
2. A clause the student derives during the proof never appeared in `state.relevant_ids`, because
   `session.record_clause` only ever appended to `clauses`. The CLI never showed this because
   `cli.py`'s own step handler separately patches its local `Board.relevant` set on every valid
   step — a client-side workaround the API never had. The browser showed every derived clause
   marked "not needed for this conclusion", including the one that closes the proof. Fixed in core
   (`record_clause` now appends to `relevant_ids` too) so the CLI's patch and the API's behaviour
   stop silently disagreeing, with a regression test (`test_a_derived_clause_is_added_to_relevant_ids`)
   added since nothing had pinned the old behaviour either way.

Both fixes were confirmed live: a full rain-paragraph proof through to the Explanation trace with
no stale "not needed" labels, and a Same-fact merge on an 8-fact paragraph correctly regrouping two
phrases and re-lettering the rest. `npm run build` is green; `pytest`, `ruff check`/`format`, the
C901 and function-length gates are green on the modified core files.

---

**Date:** 2026-10-12
**Phase:** Sprint block S8 — pilot E5 tooling, `run_experiments.py`, `heldout_eval.py`
**Tool:** Claude Code (Sonnet 5)
**Files created:** `docs/pilot/template.csv`, `consent.md`, `protocol.md`, `pre_test.md`,
`post_test.md`; `scripts/report.py`, `analyze_pilot.py`, `run_experiments.py`, `heldout_eval.py`;
`docs/results.png`, `docs/results_simulation.csv`, `docs/experiments/run_experiments.md`
**Files modified:** `backend/tests/test_dead_references.py` (PLANNED entries removed as each file
landed)
**What the student changed by hand:** none yet — to confirm.
**Purpose:** Pilot tooling first, since the classmate pilot runs today and needs the session
materials ready; then the two remaining evaluation scripts named in HLD section 11.

The pilot pre-test and post-test are deliberately PARALLEL forms — same five question types, same
point value, different letters and topics — so the post-test is not simply a memory check of the
pre-test's exact items.

`run_experiments.py`'s simulation graph needed one design decision the HLD text left open: what
the three bars measure. The resolution, confirmed with the student, is the premature-release rate
(% of simulated learners released while truly unmastered) rather than mean exercises (equal by
construction once the baseline's N is matched to the adaptive arm's mean) or final mastery at a
fixed budget (which averages away exactly the slow-learner cutoff the rule exists to catch). Mean
exercises and mean over-practice are reported in the CSV and the figure caption only. Running the
script twice and diffing the output caught a real bug before it shipped: seeding a per-walk RNG
from `hash((exercise_id, walk))` is not reproducible, because Python randomises string hashing per
process by default — fixed to a plain integer offset from `config.RANDOM_SEED`.

`heldout_eval.py` is ready but has nothing to evaluate yet: `data/heldout_paragraphs.json` is
written by the student and classmates after the parser is frozen, never by Claude (CLAUDE.md rule
6). It was verified two ways without that file — run with none present (reports "not yet run"
rather than fabricating a number) and against an uncommitted scratch fixture exercising the real
parse-and-aggregate path and the malformed-schema error case.

Every number in `docs/results.png`, `docs/results_simulation.csv` and
`docs/experiments/run_experiments.md` came from an actual run of the script, stamped with the
commit it was measured against (CLAUDE.md rule 10) — none were written by hand.

---

## S10 deck add-on | 2026-10-23 | Antigravity (Claude) | commit 1bb38b2

**Files modified:** ackend/tests/test_dead_references.py, docs/report/build_deck.py, docs/report/ProofPilot_Progress_Report.pptx`r

**What the agent did:**
- Removed 5 docs/report/*.md keys from PLANNED in 	est_dead_references.py that now exist (committed in eed9ecf). Sprint-autonomy defect fix.
- Fixed 9 ruff findings in uild_deck.py: I001 (import order), F401 (unused Emu), B008 (Pt() in default arg -> module-level _DEFAULT_LINE_WIDTH), 6x E501 (section comment lines shortened). uff check and uff format --check both clean.
- Committed ProofPilot_Progress_Report.pptx (built from the eed9ecf report kit). Commit count updated to live value: 71 commits / 58 Co-Authored-By (kit had 70/58 at 9d5b0bf).

**What the student changed by hand:** Nothing for this block (student confirmed skipping pptx regeneration).
