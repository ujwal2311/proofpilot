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
