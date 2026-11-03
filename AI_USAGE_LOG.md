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

**Files modified:** backend/tests/test_dead_references.py, docs/report/build_deck.py, docs/report/ProofPilot_Progress_Report.pptx

**What the agent did:**
- Removed 5 docs/report/*.md keys from PLANNED in test_dead_references.py that now exist (committed in eed9ecf). Sprint-autonomy defect fix.
- Fixed 9 ruff findings in build_deck.py: I001 (import order), F401 (unused Emu), B008 (Pt() in default arg -> module-level _DEFAULT_LINE_WIDTH), 6x E501 (section comment lines shortened). ruff check and ruff format --check both clean.
- Committed ProofPilot_Progress_Report.pptx (built from the eed9ecf report kit). Commit count updated to live value: 71 commits / 58 Co-Authored-By (kit had 70/58 at 9d5b0bf).

**What the student changed by hand:** Nothing for this block (student confirmed skipping pptx regeneration).

---

## S10 maintenance verification | 2026-10-24 | Codex (GPT-5)

**Files modified:** AI_USAGE_LOG.md

**Ignored verification files created:** venv/verify_deck.py, venv/docs/report/ProofPilot_Progress_Report.pptx

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Corrected control characters in the preceding S10 log entry. Built the committed deck generator in an ignored verification environment and compared it to the committed deck: 10 slides, with matching shape counts, text, and table contents. The committed deck did not require regeneration.

---

## Sprint block S6 | 2026-10-24 | Codex (GPT-5)

**Files created:** backend/src/core/formula.py, backend/src/core/translation.py, backend/src/core/narrate.py; backend/tests/test_formula.py, backend/tests/test_translation.py, backend/tests/test_narrate.py

**Files modified:** backend/tests/test_dead_references.py, AI_USAGE_LOG.md

**What the student changed by hand:** Nothing for this block (student instructed to continue in auto mode).

**Purpose:** Implemented the M2 pure-core formula parser, exhaustive translation equivalence and fixed diagnosis checker, plus ordered proof narration. The new tests cover all six M2 test-plan behaviours named in the frozen HLD.

---

## Sprint block S11 (Block 1) | 2026-10-24 | Claude Code (Sonnet 5)

**Files created:** none (committed pre-existing untracked files)

**Files modified:** data/eval/tfl_simple_tier_15.json, data/eval/tfl_stress_set_15.json (added to git), AI_USAGE_LOG.md

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `docs/report/CONTRIBUTION_TEMPLATE.md` and `FACTS.md` already documented and referenced these two AI-generated evaluation sets (`"source": "AI-generated (Claude)"` on every item, 15 items each), but the files themselves were never committed, so CI's dead-reference check failed on every fresh checkout for the last 3 pushes (`test_no_doc_or_workflow_points_at_a_file_that_does_not_exist`). Committed the two files as-is, no content changes. These remain distinct from `data/heldout_paragraphs.json`, which stays unwritten and human-only.

---

## Sprint block S11 (Block 3) | 2026-10-24 | Claude Code (Sonnet 5)

**Files created:** none

**Files modified:** backend/src/core/tutor.py (`translate_trigger`), backend/src/core/session.py (`record_translation`), backend/tests/test_tutor.py (tests for both, written first)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Built the two REMAINING `core`/`core_session` items `budgets.toml` had already priced for M2 wiring: `tutor.translate_trigger` maps a `translation.check` diagnosis to its section-9 policy row (`data/policy.yaml` already has the `translate.*` rows; `app/data.py` already builds `_TRANSLATE_OUTCOMES`), and `session.record_translation` stores one Translate-stage attempt on `State.translations` (the `Translation` dataclass already existed, unused until now).

**Deliberately NOT done, and why:** the actual entry into the Translate stage -- changing `("facts", "confirm_facts")`'s destination away from `"prove"` -- was left alone. `Exercise` is explicitly "exactly the four fields" with no per-exercise translation flag, and `test_tutor.py` has an exhaustive dict-equality test asserting `TRANSITIONS[("facts", "confirm_facts")] == "prove"` today. Nothing in the frozen HLD says whether M2 makes every exercise route through Translate (a one-line table change) or only some (needs a new `Exercise` field, i.e. a schema change). Either answer changes a frozen, exhaustively-tested behaviour, so this is a design decision for the student, not something to guess at mid-sprint.

---

## Sprint block S11 (Block 4) | 2026-10-25 | Claude Code (Sonnet 5)

**Files created:** scripts/ai_eval_tfl.py, docs/experiments/ai_eval_tfl.md

**Files modified:** none

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Wired the two AI-generated evaluation sets in `data/eval/` into a real check: does ProofPilot's own entailment pipeline agree with each item's `expected_follows`? Result: 15/15 agree on the simple tier. Deliberately a NEW, separately-named script rather than reusing `scripts/heldout_eval.py` -- that script is T1, dedicated to the human-only `data/heldout_paragraphs.json` (CLAUDE.md rule 6), and its docstring and schema are built around that file alone; routing AI-generated data through the same tool and the same output file was the exact blur the task asked to avoid. The stress-tier file has a different schema (per-sentence translation drills, no `conclusion` or `expected_follows` field at all), so it has nothing to agree or disagree about; the script reports its item count honestly instead of inventing a comparison. Note: there are two files in `data/eval/`, not three.

---

## Sprint block S11 (Block 2, continued) | 2026-10-25 | Claude Code (Sonnet 5)

**Files created:** none

**Files modified:** backend/tests/test_translation.py, backend/tests/test_narrate.py, docs/experiments/mutation_log.md (the two earlier commits this block made to data/mutants.json are logged above, under "Block 2")

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Completed the mutation refresh: ran the full set for all six modules with no score on record (session.py, tutor.py, config.py, formula.py, translation.py, narrate.py) against the real test suite. 41/43 caught on the first pass; two genuine survivors (translation.py's TR6, narrate.py's N1+N2) were fixed by adding a missing test each, never by excusing the gap or weakening a mutant. Final: 43/43 caught, logged in docs/experiments/mutation_log.md with the exact commit and fingerprint.

---

## Gate (post-progress-v1), part 1 of 2 | 2026-10-25 | Claude Code (Sonnet 5)

**Files created:** none

**Files modified:** backend/src/core/tutor.py (`TRANSITIONS[("facts","confirm_facts")]` value only), backend/tests/test_tutor.py (two assertions updated to match, one renamed)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student's explicit design-change request: `confirm_facts` now routes to `"translate"` for every exercise, universally, not conditionally -- no `Exercise` schema change, since there is no per-exercise flag and none was added. Cost: zero net code lines (one dict value changed; `tools/loc.py --strict` confirms `core` unchanged at 876). `test_every_transition_lands_where_the_design_says`: value changed (`"prove"` -> `"translate"`), scope/intent unchanged -- still the full destinations table, asserted verbatim. `test_confirming_facts_leaves_for_prove_in_m1`: value changed AND renamed to `test_confirming_facts_always_leaves_for_translate` -- the old name asserted an "in M1" conditionality that no longer exists. This surfaced that `api/main.py`'s `_translate` stub and the `board` test fixture (used by ~17 tests across test_api.py/test_api_hardening.py/test_pilot_log.py) now need a real Translate implementation to reach "prove" at all -- reported to the student rather than built further; see the gate report for the full cost/design analysis and the exact bucket numbers.

---

## FOL gate 1: HLD/CLAUDE.md doc reconciliation | 2026-10-31 | Claude Code (Sonnet 5) | commit d4b4249

**Files created:** none

**Files modified:** `docs/HLD.md` (v2.13 -> v2.14; new §18 FOL Scope Addendum merged in, carried over from a standalone review draft `FOL_Architecture.md` the student had prepared externally), `CLAUDE.md` (version pointer; `DO NOT BUILD` list loses "first-order logic or unification", replaced by a pointer to HLD §18), `backend/tests/test_dead_references.py` (PLANNED entries added for the six not-yet-built FOL modules HLD §18 names), `README.md`, `docs/READING_GUIDE.md` (stale `v2.13` references corrected).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Claude initially refused to start implementing FOL because `CLAUDE.md`'s `DO NOT BUILD` list and the frozen `docs/HLD.md` v2.13 both explicitly excluded first-order logic, which conflicted with the external `FOL_Architecture.md` draft's claim of "professor-approved" scope -- flagged as a genuine conflict between an external, unverified document and the repo's own frozen design docs, rather than acted on unilaterally. The student confirmed the professor-approved scope change directly in chat and asked for the merge; the external draft's own content was carried into HLD §18 (correcting one internal inconsistency found while merging: it called itself an "Addendum to v2.11", but the actual frozen base was already v2.13). Re-running the baseline surfaced two more real, unrelated-to-FOL gaps the merge itself exposed: a dead-reference guard failure (the new HLD text named six modules that did not exist yet -- fixed via the guard's own existing `PLANNED` allowlist mechanism, not by weakening the test) and three stale `v2.13` version references in `README.md`/`docs/READING_GUIDE.md` that a different, unrelated test already existed to catch.

**Final state:** `pytest backend/` -- 0 failures (baseline re-established). No code written. `budgets.toml` untouched at this gate.

---

## FOL gate 2: core_fol budget bucket | 2026-10-31 | Claude Code (Sonnet 5) | commit 26c34e7

**Files created:** none

**Files modified:** `budgets.toml` (new `[core_fol]` bucket, cap/ceiling sized off the HLD §18.10 estimate, 1 under that estimate's round number only to avoid colliding with an unrelated pre-existing number already in HLD §12/§15's history; `[core_session]`'s cap/ceiling raised for the Phase 8 session-wiring estimate; `[core]`'s exclude list gains the six new FOL module paths; `[totals]` extended), `backend/tests/test_loc.py` (frozen-bucket-list test extended to include `core_fol`, with the one-time exception documented in its own docstring), `CLAUDE.md` (`NO MORE BUCKETS` note gains this one named exception), `docs/HLD.md` (§18.10/§18.13 updated to record the gate).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Before Phase 1, `[core]` and `[core_session]` were found to have only single-digit-line ceiling headroom for reasons unrelated to FOL, which would have crossed a ceiling on the very first new module written -- stopped and asked per the sprint's explicit rule, rather than starting Phase 1 and discovering it mid-phase. Student said "approved, add the bucket" explicitly; `[core_fol]` was sized off the HLD §18.10 estimate.

**Final state:** `pytest backend/` -- 0 failures. `tools/loc.py` reports the new bucket; no cap or ceiling crossed by this gate itself (0 FOL code lines exist yet).

---

## FOL Phase 1: core/fol_models.py | 2026-10-31 | Claude Code (Sonnet 5) | commit 3c11437

**Files created:** `backend/src/core/fol_models.py`, `backend/tests/test_fol_models.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `fol_models.py` `PLANNED` entry removed, now that it exists)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Data model only, per HLD §18.1 and the §18.12 phase order: `Term` (`Variable`/`Constant`/`FunctionTerm`), `Predicate`, `FolLiteral`, `FolFormula` (`FolNot`/`FolAnd`/`FolOr`/`FolImplies`/`FolIff`/`ForAll`/`Exists`), `FolClause`, `Substitution` -- all frozen dataclasses, no behaviour. Tests cover frozen-ness, structural equality/hashing, and quantifier-order distinctness (`ForAll(x, Exists(y, ...))` must not equal `Exists(y, ForAll(x, ...))`).

**Final state:** `pytest backend/` -- 886 passed, 1 skipped (20 new tests, all passing on first run). `ruff` + `C901` + function-length: clean. `core_fol`: 45 lines against its cap.

---

## FOL Phase 2: core/fol_cnf.py steps 1-3 | 2026-10-31 | Claude Code (Sonnet 5) | commit 0dcf5a0

**Files created:** `backend/src/core/fol_cnf.py`, `backend/tests/test_fol_cnf.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `fol_cnf.py` `PLANNED` entry removed)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `eliminate_iff_implies`, `push_negation_inward`, `standardize_variables` -- the first 3 of the 8-step CNF pipeline (HLD §18.3). The quantifier De Morgan case (`push_negation_inward`) was split into a private `_push_not` helper to clear the `C901` complexity gate, not simplified away -- each of its 6 cases is a distinct De Morgan law. `standardize_variables` uses a rename map threaded through recursion so a quantifier that shadows an outer variable name gets its own fresh name without the outer rename leaking into it; verified against HLD §18.3's 3 pinned examples (nested same-name `ForAll`, mixed `ForAll`/`Exists`, free variables) and the quantifier-De-Morgan case the HLD flags as most commonly implemented wrong.

**Final state:** `pytest backend/` -- 906 passed, 1 skipped (20 new tests, all passing on first run). `ruff` + `C901` + function-length: clean. `core_fol`: 151 lines against its cap.

---

## FOL Phase 3: core/fol_cnf.py steps 4-8 + to_fol_clauses | 2026-10-31 | Claude Code (Sonnet 5) | commit b5e82fb

**Files created:** none

**Files modified:** `backend/src/core/fol_cnf.py` (`skolemize`, `drop_universal_quantifiers`, `distribute_and_over_or`, `flatten_to_clauses`, `standardize_apart_clauses`, `to_fol_clauses` added), `backend/tests/test_fol_cnf.py` (tests for all 5), `backend/src/core/config.py` (`MAX_FOL_CLAUSES` added).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `skolemize` replaces an existential with a fresh constant (no enclosing `ForAll`) or a function of the enclosing universals; `distribute_and_over_or` carries the `FolCNFExplosionError` clause-count guard, checked once at the true top level rather than per recursive call; `standardize_apart_clauses` renames per-clause (`c0_x`/`c1_x`), ordered by a local deterministic sort key so clause-index assignment never depends on frozenset iteration. `to_fol_clauses()` was first written to run all 8 steps, including step 8 -- re-reading HLD §18.6's `fol_prove` procedure against §18.3's step list, before writing `fol_search.py`, caught that step 8 must run ONCE over the union of every premise's clauses, not once per premise (otherwise two premises' independently-numbered variables could collide before the combined set is ever seen) -- fixed at this phase, not retrofitted later.

**Final state:** `pytest backend/` -- 929 passed, 1 skipped (43 new tests; one test's expected literal ORDER was wrong on first run, fixed to match the actual, correct output order, not the algorithm). `ruff` + `C901` + function-length: clean. `core_fol`: 296 lines against its cap.

---

## FOL Phase 4: core/unify.py | 2026-10-31 | Claude Code (Sonnet 5) | commit 2703dab

**Files created:** `backend/src/core/unify.py`, `backend/tests/test_unify.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `unify.py` `PLANNED` entry removed)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `occurs`, `apply_subst` (chain-following), `compose`, `unify`, `unify_literals` (HLD §18.4). `unify()`'s type was deliberately widened to `Term | Predicate`: HLD §18.4.3 types it as `Term`-only but lists "Predicate vs Predicate" among its own match cases, and §18.4.4 describes `unify_literals` as returning "the MGU of the two predicates' argument lists" without re-stating a name/arity check of its own -- read together, that logic lives once in `unify()`, reused for both `FunctionTerm` and `Predicate`; documented in the module docstring as a resolved ambiguity, not a guess.

**Final state:** `pytest backend/` -- 955 passed, 1 skipped (26 new tests, all passing on first run, including HLD §18.4.5's full required-test table and the multi-argument Teaches/Knows case). `ruff` + `C901` + function-length: clean. `core_fol`: 359 lines against its cap.

---

## FOL Phase 5: core/fol_resolve.py | 2026-10-31 | Claude Code (Sonnet 5) | commit a76b5f9

**Files created:** `backend/src/core/fol_resolve.py`, `backend/tests/test_fol_resolve.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `fol_resolve.py` `PLANNED` entry removed)

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `apply_literal_subst`, `is_tautology_fol`, `resolve` (one complementary unifiable pair per pivot, MGU applied to every surviving literal from both parents -- the soundness requirement HLD §18.5 names explicitly), `canonical_literal`/`canonical_clause`. HLD §18.9 Test A (Socrates, both steps) and Test E (Teaches/Knows) were hand-traced before running. One test's own expectation was wrong on the first write (a "several pivots produce several resolvents" case that actually resolves to two tautologies, not two resolvents) -- caught by the hand trace before it could hide a real bug, fixed in the test, not the implementation.

**Final state:** `pytest backend/` -- 971 passed, 1 skipped (16 new tests, all passing after the one test-expectation fix). `ruff` + `C901` + function-length: clean. `core_fol`: 385 lines against its cap.

---

## FOL Phase 6: core/fol_english.py | 2026-10-31 | Claude Code (Sonnet 5) | commit ff5a911

**Files created:** `backend/src/core/fol_english.py`, `backend/tests/test_fol_english.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `fol_english.py` `PLANNED` entry removed), `backend/tests/test_normalisation.py` (the allowed-`.lower()`-callers list extended to include `fol_english.py`, with the reason documented in that test's own docstring).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** All 11 patterns from HLD §18.2.2 (quantified, ground/relational, wh-patterns) and the 5 named errors from §18.2.4. Two gaps found and closed during implementation, beyond the design doc: (1) a reserved-word guard, without which "Every human likes every dog" would have silently become one bogus predicate instead of being refused; (2) `FOL_AMBIGUOUS_INDIVIDUAL`/`FOL_UNSUPPORTED_ARITY` are cross-sentence checks the single-sentence design text gave no mechanism for (English never spells a bound variable's name, so "used as a constant and a variable" has no literal referent) -- implemented via an optional `registry` dict threaded across a paragraph's sentences.

**Final state:** `pytest backend/` -- 999 passed, 1 skipped (28 new tests; first full run found one real test-suite defect, `test_no_core_module_normalizes_text_itself` not yet knowing about the new module -- fixed by extending that test's own allowlist, which is its designed extension point, not by weakening it). `ruff` + `C901` + function-length: clean. `core_fol`: 586 lines against its cap.

---

## FOL Phase 7: core/fol_search.py | 2026-10-31 | Claude Code (Sonnet 5) | commit 3446785

**Files created:** `backend/src/core/fol_search.py`, `backend/tests/test_fol_search.py`

**Files modified:** `backend/tests/test_dead_references.py` (the `fol_search.py` `PLANNED` entry removed), `backend/src/core/config.py` (`MAX_FOL_SEARCH_WORK` added).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** `fol_prove` (HLD §18.6): two phases sharing one `Work` budget -- saturate the premises ALONE first, then clausify premises + negated conclusion fresh and saturate that for PROVED/BUDGET_EXHAUSTED. A first version checked only "empty clause already present" per §18.6's literal step list, which is unreachable in practice (clausifying one formula alone can never produce a literally-empty clause); a hand-built contradictory-premises test caught it returning `PROVED` instead of `INCONSISTENT` -- fixed with the two-phase design, matching `messages.yaml`'s own "before the conclusion was even used" wording, not by weakening the test. Saturation deliberately re-examines every clause pair each round (mirroring `core.search`'s own `combinations()` precedent) rather than only new-vs-old pairs, documented as a deliberate simplicity choice.

**Final state:** `pytest backend/` -- 1008 passed, 1 skipped (9 new tests; one real defect found and fixed as above, not left in). `ruff` + `C901` + function-length: clean. `core_fol`: 653 lines against its cap; `core`: 935 lines, 5 under its ceiling (the `MAX_FOL_SEARCH_WORK` config line).

---

## FOL Phase 8 (detection only): mode detection in session.py | 2026-10-31 | Claude Code (Sonnet 5) | commit 0b99956

**Files created:** none

**Files modified:** `backend/src/core/fol_english.py` (`is_fol_formula`, `is_fol_sentence`, `detect_mode` added), `backend/src/core/session.py` (`Analysis` gains a `logic_mode` field, computed via `detect_mode()`; the propositional pipeline itself unchanged), `backend/tests/test_fol_english.py`, `test_tutor.py` (new assertions), `docs/HLD.md` (§18.7 rewritten to record the re-scoping below).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** HLD §18.7 originally said mode is "stored on `State.mode: Literal['prop','fol']` (new field)" and FOL exercises "go through `fol_prove()` instead of `entail()`". Neither survived contact with the actual state of the repo: `State.mode` already means `"practice"|"own_question"` (a name collision the design text missed), `[core]` had 5 lines of ceiling headroom (nowhere near enough for a field safely), and `State.entailment`'s `Verdict`/boolean-`counterexample` shape is a genuine type mismatch for `FolProofOutcome`, not a missing case -- `BUDGET_EXHAUSTED` has no boolean-assignment counterexample to offer. Stopped and asked rather than guessing a fix; student chose "detection only" for this phase, full integration named and deferred as **Phase 8b**. Separately, implementing `is_fol_formula` found HLD §18.7's own detection rule ("quantifier OR an arity>0 predicate selects FOL mode") to be unreliable: "Alice likes Bob" and the ordinary propositional "We get wet" parse by the identical NAME-verb-NAME pattern, so the arity-based half flagged ordinary sentences as FOL too -- `is_fol_formula` now checks only for `ForAll`/`Exists`.

**Final state:** `pytest backend/` -- 1020 passed, 1 skipped. `ruff` + `C901` + function-length: clean. `core_fol`: 676 lines against its cap. No `State`/`core/entail.py` change made.

---

## FOL Phase 9 (re-scoped): fol: wording in messages.yaml | 2026-10-31 | Claude Code (Sonnet 5) | commit 89e3a38

**Files created:** none

**Files modified:** `data/messages.yaml` (`fol:` section: `proved`/`budget_exhausted`/`inconsistent` wording, per HLD §18.6.4), `docs/HLD.md` (§18.12's Phase 9/10 rows re-scoped).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Phase 9 originally also exposed `mode` over the API and added a frontend banner -- both assumed the Phase 8b session wiring Phase 8 had just deferred, so there was nothing yet to expose. Shipped only the wording, unconsumed by any code path at the time, reviewable ahead of the wiring that would need it.

**Final state:** `pytest backend/` -- 1020 passed, 1 skipped (unchanged -- no code path read this section yet).

---

## FOL Phase 10 (re-scoped): pipeline-level integration from text | 2026-10-31 | Claude Code (Sonnet 5) | commit bc50269

**Files created:** `backend/tests/test_fol_integration.py`

**Files modified:** none

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The original Phase 10 ("full integration tests") assumed the session/API-level wiring Phase 8 had just deferred to Phase 8b. Re-scoped to pipeline-level: real English paragraphs through `fol_english.parse()` -> `fol_prove()`, end to end -- Socrates (PROVED), unrelated quantified predicates (BUDGET_EXHAUSTED), contradictory ground facts (INCONSISTENT), a tiny budget (no crash), a second vocabulary (not special-cased), and a named confirmation that multiply-quantified binary relations are out of scope (HLD §18.2/§18.8) -- which is also why the Teaches/Knows premise from HLD §18.9 Test E stays a hand-built-`FolFormula` test in `test_fol_search.py` rather than a text-parsed one here.

**Final state:** `pytest backend/` -- 1027 passed, 1 skipped (7 new tests, all passing on first run). `ruff` + `C901` + function-length: clean. This closed the originally-scoped Phases 1-10; all ten phases and the two gates preceding them committed locally, one commit per phase/gate, nothing pushed yet at this point.

---

## FOL Phase 8b: session.py calls fol_prove(), via State + API + frontend | 2026-10-31 | Claude Code (Sonnet 5) | commits 8e9e447, 30bb400

**Files created:** none

**Files modified:** `backend/src/core/fol_search.py` (`FolSessionResult` added), `backend/src/core/models.py` (`State.fol_result: FolSessionResult | None` added), `backend/src/core/session.py` (`_fol_attempt()` and `_parse_sentences()` added; `analyse()` now calls `fol_prove()` for FOL-mode sessions), `backend/tests/test_models.py`, `test_state_roundtrip.py`, `test_tutor.py`, `test_api.py` (new/updated assertions), `frontend/src/ReadFacts.jsx`, `labels.js`, `index.css` (minimal display, later superseded -- see the next entry).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student reviewed the Phase 1-10 report, said to push what was already committed without waiting for Phase 8b, and asked for Phase 8b to be built as the next block: `session.py` actually calling `fol_prove()`, the `FolSessionResult` field on `State`, the API returning it, a minimal frontend display, then the session/API-level integration tests re-run and confirmed passing. Pushed the 13 prior commits first (`f6fff12..012ed53`), separate from and before this work. Re-ran the budget check at this gate as Phase 8's own note said to: `[core]` measured 3 lines under its ceiling after the field (not crossed), and `session.analyse()` came in at 64 lines against the 60-line function gate (a blocking gate) -- fixed by extracting `_parse_sentences()`. Confirmed by running, not assumed: `TypeAdapter(State)` needed no `api/schemas.py` change to serialise the new field (the state-roundtrip property test had never generated a non-`None` `fol_result` at all -- added a generator for it, closing a real pre-existing gap in that test's "every shape" coverage) and a live `uvicorn` response (not just `TestClient`) confirmed it over real HTTP. Two of the requested session-level tests needed fixing after a first run failed: the assumed-contradictory and assumed-multi-argument-relation paragraphs had no quantifier, and `detect_mode` correctly reports "prop" for a ground-only paragraph regardless of content (Phase 8's own arity-signal correction) -- fixed by adding an incidental quantified sentence to each, noted in-test as to why.

**Final state:** `pytest backend/` -- 1035 passed, 1 skipped. `ruff` + `C901` + function-length: clean. Pushed on explicit instruction (`012ed53..0f385fc`).

---

## FOL Phase 8b, continued: render messages.yaml's fol: wording | 2026-10-31 | Claude Code (Sonnet 5) | commit e1a56b6

**Files created:** none

**Files modified:** `backend/src/app/render.py` (`Renderer.fol_outcome()` added, filling the Phase 9 `fol:` templates), `backend/src/api/schemas.py` (`ParseResponse.fol_message: str | None` added), `backend/src/api/main.py` (`/api/parse` renders it), `backend/tests/test_api.py` (new assertions), `frontend/src/useSession.js`, `App.jsx` (carry/show `fol_message` the same way `warnings` already works), `frontend/src/ReadFacts.jsx`, `labels.js` (the prior block's raw-outcome display removed, now that the rendered sentence exists).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student asked for the frontend to use `messages.yaml`'s existing `fol:` strings instead of the raw enum/step-count the prior block shipped, and for a live browser screenshot once the Chrome extension was connected. The rendering change was made (verified live via `curl` against a running `uvicorn` instance: `fol_message` returns the rendered sentence, not the code). The Chrome extension was checked again and was still not connected in this environment -- reported explicitly rather than skipped or substituted with a code-inspection claim. Separately confirmed, re-checked rather than assumed: the Teaches/Knows ∀x∀y binary-relation premise cannot go through the English grammar at all (only its ground, named-constants form can; `FOL_NESTED_QUANTIFIER_IN_GROUND` fires deterministically on the quantified form), matching HLD §18.2/§18.8's documented scope boundary exactly.

**Final state:** `pytest backend/` -- 1037 passed, 1 skipped. `ruff` + `C901` + function-length: clean. `npm run build`: clean. Committed locally, not yet pushed at the time this entry was written.

---

## AI_USAGE_LOG.md restructure + screenshot closure | 2026-10-31 | Claude Code (Sonnet 5) | commits 3275619, e1a56b6 (pushed), d1843b4

**Files created:** none

**Files modified:** `AI_USAGE_LOG.md` (this file -- the three combined entries covering the doc-reconciliation gate, the budget-bucket gate, and the whole Phases 1-10 + Phase 8b sprint were split into 14 individual phase/gate entries, matching CLAUDE.md rule 5's "after every phase" requirement, which the combined form did not satisfy), `docs/HLD.md` (§18.13's sign-off checklist updated to reflect actual current state: Phases 1-10 and Phase 8b marked done and pushed, equality reasoning confirmed out of scope by explicit student statement, and -- after this entry -- the live browser screenshot item closed).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student asked directly whether the log had an entry for every phase of the FOL sprint, as CLAUDE.md requires, and whether §18.13 reflected reality -- it did not, on both counts; fixed rather than left standing. Student then approved pushing the pending commits (`3275619`, `e1a56b6`), confirmed equality reasoning stays out of scope (closing that checklist line), and asked for the live browser screenshot. The Chrome extension was checked a third time and still did not connect in this environment; rather than substitute a code-inspection claim again, the student was offered the choice to take it themselves, chose to, and the two local dev servers were started for them. The student's own screenshot (not captured by Claude) confirms the designed behaviour exactly: the propositional grammar still refuses "Every human is mortal" with `QUANTIFIER_UNSUPPORTED` unchanged, and the FOL result renders as "Valid -- the empty clause was derived in 3 step(s)." from `messages.yaml`, not a raw code, alongside the pre-existing CONCLUSION_FACT_UNSEEN warning firing independently and correctly on the same exercise.

**Final state:** `pytest backend/` -- 1037 passed, 1 skipped (unchanged -- documentation only). All of this sprint's commits are pushed through `d1843b4`. HLD §18.13's checklist is fully closed except the CLAUDE.md design-freeze items that were never part of this sprint's scope.

---

## Facts-panel fix: a FOL-understood sentence must not show a propositional error | 2026-11-01 | Claude Code (Sonnet 5) | commit 00c3e36

**Files created:** none

**Files modified:** `backend/src/core/fol_english.py` (`render()`, `display_readings()` added), `backend/src/core/models.py` (`SentenceRec.fol_reading` field added), `backend/src/core/session.py` (`_parse_sentences` suppresses a propositional refusal when the FOL grammar already understood the same sentence), `backend/tests/test_api.py`, `test_cli.py`, `test_state_roundtrip.py`, `test_tutor.py` (five pre-existing assertions updated that encoded the OLD behaviour as correct, plus one new parametrized test over all 11 HLD S18.2 grammar patterns), `frontend/src/ReadFacts.jsx`, `index.css` (render `fol_reading` next to the sentence instead of the suppressed error).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student reported, with a screenshot, that "Every fish is not a mammal" showed as a red `QUANTIFIER_UNSUPPORTED` error on the Facts screen of a FOL-mode exercise, directly contradicting the `folModeNote` banner telling the student the error "doesn't apply." This is an explicit change request superseding the design decision the previous log entry recorded as correct (the student's own screenshot there showed the identical propositional refusal and the entry called it "the designed behaviour exactly") -- CLAUDE.md requires such a change to come from the student, and it did, in detail, in this message. The propositional tree is still built unconditionally per HLD S18.0 (the Prove board's clauses still come only from it); only the sentence's DISPLAYED status/error_code now defers to the FOL grammar's own, independent reading when one exists. Verified against the exact reported scenario and all 11 grammar-table patterns, live against a running `uvicorn`/`vite` pair (Chrome extension connected for this session) -- screenshots taken for 11/11 patterns across three own-question submissions, plus the PROVED, BUDGET_EXHAUSTED and INCONSISTENT fol_message banners and the Prove board, all confirmed unaffected.

**Budget note:** `core_session` grew from 188 to 191 code lines -- exactly at its ceiling (191), not over it; `core` grew from 938 to 939 (ceiling 940); `core (FOL)` grew from 683 to 711 (cap 849). No bucket crossed a ceiling it was not already over before this change. `frontend` (already over its ceiling before this change, reported-not-blocking) grew by 4 lines.

**Final state:** `pytest backend/` -- 1051 passed, 1 skipped, both hash seeds. `ruff check` + `ruff format --check`: clean. `npm run build`: clean. Committed locally (`00c3e36`), **not pushed** -- the student's message did not contain "approved" for this gate (CLAUDE.md's absolute push rule, back in force since the `progress-v1` tag).

---

## FOL-aware hint/claim dispatch (Prove-screen follow-up) | 2026-11-01 | Claude Code (Sonnet 5) | commit 3e05d0d

**Files created:** none

**Files modified:** `backend/src/core/fol_search.py` (`fol_claim_accepted()`, `fol_hint_code()`), `backend/src/api/main.py` (`_hint`/`_claim` dispatch, `_is_fol` helper), `backend/src/app/data.py` (`required_messages()`'s hint set), `data/messages.yaml` (`HINT_FOL_FOLLOWS_1/2/3`, `HINT_FOL_UNKNOWN`), `frontend/src/Feedback.jsx` (`TONE` map), `backend/tests/test_fol_search.py`, `backend/tests/test_api.py`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student's own screenshot of a Socrates-style exercise showed `HINT_NOT_FOLLOW_1` ("check whether the conclusion really follows") directly under a "Valid -- proved in 3 steps" FOL banner -- the Prove screen's hint/claim logic consulted only the propositional verdict, never `fol_result`, so clicking "Does not follow" would have scored `CLAIM_ACCEPTED` (correct) for an argument the FOL engine had already proved. Student specified the mapping directly (PROVED/INCONSISTENT -> wrong to claim it doesn't follow; BUDGET_EXHAUSTED -> unscored), after I flagged that their initial spec named a `NOT_ENTAILED` FOL outcome that doesn't exist in `FolProofOutcome` (checked against the actual enum before implementing, not assumed). Per the student's explicit budget instruction (see the entry below), the FOL-aware logic lives entirely in `core_fol`/`api_cli` -- `tutor.py` and `session.py` are untouched, and `core`/`core_session` measure identical before and after. Verified live: Socrates (PROVED) now hints "this argument is valid..." and rejects "does not follow"; an unrelated-predicates exercise (BUDGET_EXHAUSTED) hints and claims honestly with mastery left unscored; an ordinary propositional exercise unaffected.

**Budget note:** `core`/`core_session` untouched (939/940, 191/191 -- zero headroom was available, zero was used). `core (FOL)` grew 711 -> 717 lines (cap 849). `api_cli`/`frontend` grew inside their already-over-ceiling, reported-not-blocking status at the time (see the next entry for why that status itself turned out to be wrong).

**Final state:** `pytest backend/` -- 1063 passed, 1 skipped, both hash seeds. `ruff` + format: clean. Committed locally (`3e05d0d`), not pushed.

---

## FOL grammar extension: bare intransitive verb + ground "or" | 2026-11-01 | Claude Code (Sonnet 5) | commit 21384a5

**Files created:** none

**Files modified:** `backend/src/core/fol_english.py` (`_parse_ground`, `_RESERVED`), `backend/tests/test_fol_english.py`, `docs/HLD.md` (S18.2's pattern table).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student pasted a real CAT-2 worked example ("All students who study pass the exam...") to use as the web demo. Verified against the live grammar (not assumed) which exact sentences failed and why: "who" needs "that" (trivial reword), and two genuine gaps with no workaround -- a bare intransitive ground verb ("Ravi studies", no "is", no object) and ground-level disjunction ("A or B" between two facts) were simply absent from HLD S18.2's pattern table. Student authorized exactly these two, nothing broader. Implemented as a thin recursive split inside `_parse_ground` (each side of "or" is the same function called again, so it composes with the existing "and" pattern for free) plus a `len(rest) == 1` case for the bare verb. Also discovered, debugging the worked example end-to-end, that the grammar's documented no-stemming rule ("students"/"student", "study"/"studies") blocks the example even after the grammar fix, until every predicate word is spelled identically across every sentence -- not a bug, the pre-existing, intentional design principle biting on a real paragraph. The reworded example proves successfully: `PROVED`, 22 saturation steps.

**Budget note:** `core_fol` grew 717 -> 726 lines (cap 849, 123 lines of headroom remaining). `core`/`core_session` untouched.

**Final state:** `pytest backend/` -- 1070 passed, 1 skipped, both hash seeds. `ruff` + format: clean. Committed locally (`21384a5`), not pushed.

---

## Open item, logged not deferred indefinitely: `tools/loc.py`'s stale default | 2026-11-02 | Claude Code (Sonnet 5)

**Finding (not yet acted on):** `git tag --list progress-v1` confirms the tag exists (2026-10-13) and is an ancestor of `HEAD` (43 commits behind) -- its own message states "Per CLAUDE.md's TEMPORARY SPRINT RULE, this tag ends the sprint's commit-and-push..." CLAUDE.md's TEMPORARY SPRINT RULE section, including its "bucket caps are REPORTED, not blocking" override, is therefore structurally expired and has been for every commit since. `tools/loc.py` still prints "Caps are REPORTED, not blocking (sprint rule, expires at `progress-v1`)" unconditionally unless `--strict` is passed -- the CODE was never updated to match the tag's own existence, so CI (which runs `python tools/loc.py` with no `--strict`) has been silently non-blocking on ceilings since 2026-10-13 regardless of the written rule.

**Concrete consequence found 2026-11-02:** `api_cli` (958 lines, ceiling 713 -- 245 over) and `frontend` (1553 lines, ceiling 866 -- 687 over) are both live frozen-rule violations under the correct (strict) reading, not neutral pre-existing facts as earlier entries in this log assumed.

**Decision (student, 2026-11-02):** §18.14 (FOL proof trace display) is authorized to add to both buckets anyway, as a recorded one-time exception, same precedent as `core_fol`'s own exception at the Phase 8 gate -- not a silent absorption, and not blocking tonight's work. Two concrete post-Wednesday-demo tasks, named so they are not lost:

  1. Flip `tools/loc.py`'s default from reported-to `--strict`-by-default (an explicit flag restores the old lenient behaviour if ever needed again), so CI actually enforces the written rule instead of a stale sprint override.
  2. Bring `api_cli` and `frontend` back under their ceilings -- by simplification, not by raising the caps (CLAUDE.md's frozen OVERRUN POLICY: caps are never raised).

Neither task blocks §18.14; both are scheduled after the Wednesday demo, not indefinitely deferred.

---

## FOL: predicate canonicalization, grammar extensions, minimal derivation | 2026-11-02 | Claude Code (Sonnet 5)

**Files created:** none

**Files modified:** `backend/src/core/fol_english.py` (`_canonical_word`, `_constant`, `_predicate`, `_relative_index`, `_relative_clause`, `_main_predicate`, `_parse_all_that`, `_parse_indefinite`, `_parse_ground`, dispatcher, keyword tables, module docstring), `backend/src/core/fol_search.py` (`_minimal_derivation`, `fol_prove`), `backend/tests/test_fol_english.py`, `backend/tests/test_fol_search.py`, `backend/tests/test_tutor.py`, `docs/HLD.md` (new §18.15).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The student supplied a CAT-2-style worked example as the demo centrepiece and asked for the FOL mode to teach resolution properly. Running it against the live grammar first — not assuming — found three defects, two silent:

  1. **Three sentences did not parse at all.** `"All students who study pass the exam"` (only `that` was a relative pronoun), `"Anyone who is lucky passes the exam"` (no indefinite quantifier), and the conclusion `"Ravi passes the exam"` (bare intransitive was single-word only, so verb+object was unreachable).
  2. **Nothing unified even after rewording.** The grammar's documented no-stemming rule produced `Students`/`Student` and `Study`/`Studies` as distinct symbols, so a valid argument returned `BUDGET_EXHAUSTED` — which §18.6 forbids presenting as "not provable" and which a student cannot distinguish from "no proof exists". This was the worst of the three: a silent wrong answer on the flagship example. The 2026-11-01 entry above had already observed this blocker and recorded it as intended design; running the full argument showed the trade-off was the wrong way round.
  3. **The proof trace was a search log.** `fol_prove` returned every resolvent saturation generated — 22 steps for this argument, 3 for Socrates — where the derivations are 4 and 2. §18.14's renderer printed all of them.

Fixes, all three inside `core_fol`: regular-inflection canonicalization (general rule, no word list; names never canonicalized; registry keyed canonically on both sides); the three grammar patterns; and `_minimal_derivation`, which back-chains from the empty clause through each resolvent's parents. `BUDGET_EXHAUSTED` now returns an empty derivation rather than a partial log. `app/render.py`, `api/schemas.py` and the frontend needed **no changes** — they receive a shorter, meaningful list through the existing field.

**Regression found and fixed during implementation:** canonicalizing the predicate registry key but not the constant key silently broke the `FOL_AMBIGUOUS_INDIVIDUAL` cross-role check (`"Ravi studies or Studies is a person"` stopped raising). Constants now register under a canonical key while keeping their written name as the value. Covered by the pre-existing test that caught it.

**Test expectations updated (spec change, not weakened assertions):** canonicalization renames grammar-derived predicates, so 13 assertions across `test_fol_english.py` and `test_tutor.py` moved to the canonical symbol (`Likes`→`Like`, `Studies`→`Study`, `Students`→`Student`, `Teaches`→`Teach`, `Knows`→`Know`, `Admires`→`Admire`, `Birds`→`Bird`). Every assertion kept its exact structure; only the expected symbol name changed. 23 new tests added (16 grammar/canonicalization, 7 derivation), including canonicalization checked against two vocabularies it had never seen.

**Acceptance test (the student's own condition — run, not assumed).** The exact paragraph, end to end through `fol_english.parse` → `fol_prove` → `Renderer.fol_proof_trace`:

```
Vocabulary:  ravi Constant | student, study, lucky, pass the exam  Predicate/1
∀x (Student(x) ∧ Study(x) → PassTheExam(x)) | Student(ravi)
Study(ravi) ∨ Lucky(ravi) | ∀x (Lucky(x) → PassTheExam(x)) | goal PassTheExam(ravi)
Verdict: PROVED, 4 derivation steps (was 22)
  1. F1 + F2 => F3  ¬Study(ravi) ∨ PassTheExam(ravi)
  2. F4 + F5 => F6  PassTheExam(ravi) ∨ Study(ravi)
  3. F3 + F6 => F7  PassTheExam(ravi)
  4. F8 + F7 => F9  □
```

No pipeline-internal variable name (`c2_v0`) reaches the rendered trace — the renderer's existing per-clause display naming (§18.14.2) maps them to `x`.

**Budget note:** `core_fol` grew 726 → 790 code lines and stayed **under its cap** — no exception needed, unlike §18.14. `core` (939), `core_session` (191), `api_cli` (1042), `scripts` (574) and `frontend` (1598) are **unchanged**; the two over-ceiling buckets received no new lines. CORE TOTAL 2021 → 2085, under cap. Function-length gate passes (longest 58, unchanged). See `budgets.toml` for the caps.

**Final state:** `pytest backend/` — 1107 passed, 1 skipped (was 1084). `ruff check` and `ruff format --check`: clean. `python tools/loc.py`: no new breach. Not committed, not pushed — awaiting the student's review.

**Deferred at this gate, by the student's explicit instruction — logged so they are not lost:** per-step unifier column; sentence→clause provenance and the CNF "Sentence | Working | Clause" table; the Vocabulary panel (the registry already computes it and discards it); the static FOL Quick Reference panel (when built, engine-backed rows must be marked — the engine does binary resolution with unification only, not UI/EI/UG/EG, chaining, Horn clauses, factoring or equality); and the propositional/FOL mode dropdown. For the dropdown the student recorded the decision in advance: auto-detect with manual override and a named refusal rather than a guess. These join the two post-demo tasks in the entry above (`loc.py` strict default; bringing `api_cli`/`frontend` back under ceiling).

**Open question for the student — flagged rather than guessed at.** The instruction was that canonicalization must "fail loudly when uncertain", naming the two mismatched words instead of falling through to `BUDGET_EXHAUSTED`. Canonicalization now handles every regular case, so what remains is irregular inflection (`person`/`people`, `child`/`children`). No general relatedness test was found that fires on those without also false-firing on legitimately distinct predicates sharing a stem — `Student`/`Study`, `Fly`/`Flyer` and `Pass`/`PassTheExam` all occur in the worked examples, and a prefix or edit-distance rule refuses them. Building one would have meant guessing in the opposite direction, which principle 2 forbids as firmly as the silent non-unification it was meant to prevent. **Proposal awaiting a decision:** apply the check only when the outcome is already `BUDGET_EXHAUSTED`, where a false positive costs an over-cautious message instead of a wrongly refused valid argument, and report the two candidate predicates as a possible cause rather than as a verdict.

---

## FOL exam-form proof trace: six items | 2026-11-02 | Claude Code (Sonnet 5)

**Files created:** none

**Files modified:** `backend/src/core/fol_cnf.py` (`standardize_apart_ordered`, `to_fol_clauses_traced`, `to_fol_clauses` delegates), `backend/src/core/fol_resolve.py` (`resolve` returns the MGU), `backend/src/core/fol_search.py` (`FolInputClause`, `input_clauses`, `_clausify_tagged` replacing `_clausify_all`, 4-tuple `FolProofStep`), `backend/src/core/fol_english.py` (`_term_text`, `render` fix), `backend/src/app/render.py` (`FolTraceClause`, legend, `_fol_conclusion`, `_fol_goal_text`, `_fol_unifier_text`, `_fol_tree`), `backend/src/api/schemas.py`, `data/messages.yaml`, `docs/HLD.md` (new §18.15.6), and the matching tests.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The student reviewed the §18.15 derivation output and listed what an examiner would mark down: no clause definitions, no unifiers, no CNF working, no justification for the negated goal, no exam-form conclusion, no refutation tree. Six items, specified in build order, each reported with real line counts.

**Built, in order, each verified before the next:**

  1. **Full clause legend** — every clause, including inputs the derivation never used. Needed `standardize_apart_ordered` in `fol_cnf` to expose the `(original, renamed)` pairing that `standardize_apart_clauses` computed and discarded, since origin can only be decided on the pre-renaming clause.
  2. **Negated-goal caption** — wording in `messages.yaml`, not in code, matching the existing `fol:` tone.
  3. **Exam-form conclusion** — goal recovered by flipping the negated-goal clause's polarity; emitted only for `PROVED`, never for `BUDGET_EXHAUSTED`.
  4. **Per-step unifier** — `resolve()` now returns `(resolvent, mgu)` pairs and `FolProofStep` is a 4-tuple. Reverses §18.14.5's deferral on the student's instruction.
  5. **Refutation tree** — plain indented text, no drawing library, no frontend dependency.
  6. **CNF working retained** — `to_fol_clauses_traced` keeps all six intermediates; `to_fol_clauses` delegates to it, so one pipeline exists rather than two that would drift.

**Defect found and fixed inside item 6:** `fol_english.render` printed a term's bare `.name`, so a Skolem `FunctionTerm` rendered as `sk_f0` with its arguments dropped. Invisible until the CNF working column began handing it post-Skolemization formulas. Now rendered recursively, with its own test.

**Existential verification (the student required this explicitly, since no in-scope example has an `∃`):** two synthetic cases tested and run end to end — `∃y Loves(y)` → `Loves(sk_c0)`, and `∀x ∃y Loves(x,y)` → `∀v0 Loves(v0, sk_f0(v0))` → clause `Loves(x, sk_f0(x))`. Skolem constant and Skolem function of the enclosing universal both render correctly.

**Regression safety (item 6 touches the shared CNF pipeline):** full suite after every item, not just the new tests, plus both hash seeds at the end. No regression at any point. Test expectations updated only for the deliberate shape changes (`resolve`'s return, `FolProofStep`'s arity) — every assertion kept its structure.

**Acceptance, re-run on the exact paragraph:**

```
F1 ¬Lucky(x) ∨ PassTheExam(x)                [premise]
F2 ¬PassTheExam(ravi)                        [negated_goal] <- Negated for refutation...
F3 ¬Student(x) ∨ ¬Study(x) ∨ PassTheExam(x)  [premise]
F4 Lucky(ravi) ∨ Study(ravi)                 [premise]
F5 Student(ravi)                             [premise]
1. F3 + F5 -> F6  unifier: x = ravi     2. F1 + F4 -> F7  unifier: x = ravi
3. F6 + F7 -> F8  (none)                4. F2 + F8 -> F9 = □
F1 ∧ F3 ∧ F4 ∧ F5 together with F2 is unsatisfiable, so PassTheExam(ravi) is proved.
```

**Budget, measured per item (code lines):**

| After item | core_fol | api_cli | frontend |
|---|---|---|---|
| start | 805 | 1042 | 1598 |
| 1 legend | 819 | 1061 | 1598 |
| 2+3 caption, conclusion | 819 | 1092 | 1598 |
| 4 unifier | 819 | 1103 | 1598 |
| 5 tree | 819 | 1121 | 1598 |
| 6 CNF trace | 830 | 1121 | 1598 |
| 6 render fix (same item) | 835 | 1121 | 1598 |

`core_fol` finished **under its cap** (849) with headroom to its ceiling (934). `frontend` was **never touched**. `api_cli` grew 79 lines and is further past a ceiling it already exceeded under §18.14.6's recorded exception.

**STOP-AND-REPORT, per CLAUDE.md:** **CORE TOTAL crossed its cap at item 6** — 2114 → 2130 against a cap of 2121, i.e. 9 lines over, still well under the 2335 ceiling. `core_fol` alone is fine; the combined figure is not. CLAUDE.md requires a bucket between cap and ceiling be justified at a gate, and the combined CORE TOTAL exists precisely so a split bucket cannot present its cost as separate small ones. Reported, not absorbed, and no cap re-based.

**Known defect found, deliberately NOT fixed (needs its own gate):** `fol_english.render` emits no parentheses around nested connectives, so an intermediate CNF step prints as `¬Student(x) ∧ Study(x) ∨ PassTheExam(x)` — correct as a tree, ambiguous as text, misleading in a working column where precedence is the whole point. Fixing it churns many expected strings across the FOL tests, so it is logged rather than absorbed into this gate.

**Final state:** `pytest backend/` — 1136 passed, 1 skipped (was 1117 at the start of these six items), both hash seeds. `ruff check` + `ruff format --check`: clean. Function-length and complexity gates: pass. Not committed, not pushed.

---

## FOL rendering gap: the page now shows what the API already sent | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `frontend/src/FolExplanation.jsx` (rewritten), `frontend/src/useSession.js`, `frontend/src/storage.js`, `frontend/src/ReadFacts.jsx`, `frontend/src/App.jsx`, `frontend/src/labels.js`, `frontend/src/index.css`, `backend/src/core/session.py` (one expression).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The Phase 1 fresh-eyes pass found that every exam-form field built tonight reached the browser and none of it was drawn. Five fixes, all authorized as completing Phase 1 rather than new scope:

  1. **`FolExplanation.jsx` rewritten** to render the clause legend with origin tags, the negated-goal caption, per-step unifiers (plus each resolvent's own text, so a step is readable without scrolling back to the legend), the refutation tree (a `<pre>` over the server's indented text -- no drawing library), and the exam-form conclusion.
  2. **Propositional diagnostics scoped out of FOL mode** (`session.py`): `CONCLUSION_FACT_UNSEEN` fired "the conclusion mentions X, which no premise does" directly above a FOL "Valid" verdict. Not made FOL-aware -- the propositional pipeline's findings describe a reading the session is not being judged by, so they are dropped in FOL mode.
  3. **Restored session keeps its verdict.** `storage` now saves an envelope `{state, fol}` instead of a bare `State`; `useSession` holds the FOL pair in a ref so `keep` persists it without every caller knowing about it. A bare-State save from an older build has no `state` key and is dropped the same way an unparseable one is.
  4. **"Next exercise" no longer appears on a self-entered argument** -- it offers "New argument" when `state.mode === "own_question"`.
  5. **Facts panel hidden in FOL mode.** The propositional atoms are real but were never used by the proof shown above them; asking the student to vet them next to a finished first-order proof is misleading. The sentence list stays -- that is where each FOL reading is shown.

**Latent bug found and fixed in passing:** `nextExercise` never cleared the FOL pair, so the previous argument's verdict rode along into the next exercise. Cleared before the request.

**Verified in the running app, not by code read** (`uvicorn` + `vite`, Chrome): the Ravi argument renders legend/origins/caption/unifiers/tree/conclusion; a reload preserves verdict AND trace; the button reads "New argument"; the contradictory banner is gone; the Facts panel is absent. A propositional argument ("If it rains...") still shows facts, merge UI and confirm button unchanged -- no regression. Screenshots could not be captured: `Page.captureScreenshot` timed out three times at the CDP layer while the page itself stayed responsive to text extraction, so the verification above is from live page text rather than images.

**Budget:** `frontend` 1598 -> 1704 (+106), already past its ceiling -- the student authorized this explicitly ("proceeds regardless of ceiling status, since the alternative is a demo where tonight's work doesn't exist on screen"). `api_cli` 1123, `core_session` 191, `core_fol` 867 -- all unchanged. `CORE TOTAL` 2162, unchanged.

**Final state:** `pytest backend/` -- 1159 passed, 1 skipped. `ruff` clean. `npm run build` clean. Not committed, not pushed.

---

## §18.16 step 1: bucket cleanup -- honest simplification attempt | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/core/fol_english.py`, `docs/HLD.md` (§18.16 applied).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**`core_fol` -- the harder answer worked.** 867 -> **847 code lines, back under its cap**, with the ceiling 87 lines away. One genuine consolidation, not cosmetic line-joining: `_parse_every`, `_parse_no` and `_parse_some` were character-for-character identical apart from the node they built (33 code lines across three functions). They are now one `_parse_simple_quantified` (16 lines) plus a two-branch `_parse_quantified` (4, from 8). Contract unchanged -- same ASTs, same refusals, same error codes -- and all 1159 tests stayed green through the change.

Stopped there deliberately. The next candidate was `fol_cnf.py`'s five step functions, which share a recursive match-statement shape; collapsing them into a generic walker would be the single highest-risk refactor of the night, on the most correctness-sensitive module, for a bucket already under its cap. CLAUDE.md's "correctness of the logic output matters more than feature count" and the student's own framing both point the other way.

**`frontend` and `api_cli` -- the gap is structural, not slack.** Honest attempt made, real shortfall reported rather than papered over:

| bucket | code | ceiling | shortfall |
|---|---|---|---|
| `frontend` | 1704 | 866 | **838** |
| `api_cli` | 1123 | 713 | **410** |

What the measurement actually shows:

  1. **`index.css` is 699 of `frontend`'s 1704 -- 41% of the bucket is a stylesheet.** The `frontend` pattern includes `**/*.css`, so a cap whose stated purpose is to bound *logic complexity* is being spent on styling. The JS/JSX alone is 1005 lines across 13 components -- still over 866, but a very different number from 1704.
  2. **The CSS is not bloated.** Of 63 classes, exactly one (`.md`) is unreferenced by any JS/JSX. There is no dead-rule harvest to take.
  3. **`api_cli`'s size is deliberate design.** `main.py` (319) and `cli.py` (212) overlap because HLD §4 requires the whole tutor to work with no web layer -- the CLI gate (`test_cli.py`) exists to enforce that. Deduplicating them would break a design decision to satisfy a line count.

**Conclusion, stated plainly:** neither ceiling is reachable by simplification. These caps were set when the app was a fraction of its current size and were never revisited, and the frozen OVERRUN POLICY forbids raising them. The honest options are (a) exclude `*.css` from the `frontend` pattern, since a stylesheet is not the logic complexity the cap exists to bound -- a change to what is measured, not to a cap number; or (b) a recorded standing exception for both buckets, same shape as §18.14.6. **This is the student's call, not Claude's** -- flagged, not absorbed, and no cap re-based.

**Final state:** `pytest backend/` -- 1159 passed, 1 skipped. `ruff` clean. Not committed, not pushed.

---

## §18.16 step 1b: CSS unmeasured + standing exception | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `budgets.toml` (`[frontend]` patterns), `backend/tests/test_loc.py` (`MEASURED_TREES`), `docs/HLD.md` (§18.16.6).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Student chose option (a) from the cleanup gate and asked for it as a permanent change to how measurement works, not a one-off. Note on where it landed: the pattern lives in `budgets.toml`, not in `tools/loc.py` (which reads it), so the change is there plus the matching entry in `test_loc.py`'s `MEASURED_TREES` -- without the second, `index.css` would have matched no bucket and `test_every_source_file_is_measured_by_exactly_one_bucket` would have failed, which is that guard working correctly.

**Measured result of the exclusion:** `frontend` 1704 -> **1005** code lines. Ceiling 866, so **139 over** -- the student's own estimate was "roughly 139". `api_cli` unchanged at 1123, **410 over** its ceiling, untouched by the CSS change exactly as the student said it would be.

**Standing exception recorded** (HLD §18.16.6) for `frontend`'s remaining 139 and `api_cli`'s full 410, same shape as §18.14.6. Both confirmed non-simplifiable by the step-1 analysis: `frontend` has 13 components, no duplicated component, and 62 of 63 CSS classes referenced; `api_cli`'s `main.py`/`cli.py` overlap is required by HLD §4's no-web-layer guarantee and enforced by `test_cli.py`. No cap re-based, no bucket added, exception scoped to these two buckets only.

**Final state:** `pytest backend/` -- 1159 passed, 1 skipped. `ruff` clean. Not committed, not pushed.

---

## §18.16 step 2: `fol_step` module + tests | 2026-11-02 | Claude Code (Sonnet 5)

**Files created:** `backend/src/core/fol_step.py`, `backend/tests/test_fol_step.py`.
**Files modified:** `budgets.toml` (bucket assignment).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The step validator from HLD §18.16.2. Contract written first (purpose, signatures, four invariants, a five-step diagnosis order, edge cases), then 17 tests, then the implementation.

`check_fol_step(a, b, typed) -> FolStepError | None` returns `None` for exactly the clauses `resolve()` produces, and names the most specific mistake otherwise: `NOT_COMPLEMENTARY` (no literal pair shares a predicate at opposite polarity), `NO_UNIFIER` (a pair exists but nothing unifies -- the occurs check included, since that is a teachable fact, not an internal detail), `DOUBLE_RESOLVE` (two pairs cancelled in one step), `SUBST_INCOMPLETE` (§18.5's unsoundness: the MGU applied only where the clauses were resolved), and `WRONG_RESOLVENT` as the honest fallback.

**Legality is decided by `resolve()` alone.** The pivot enumeration in this module exists only to classify a step `resolve` has already rejected. Two implementations of the resolution rule would eventually disagree, and the one a student is graded against would be the wrong one.

**Design note on `DOUBLE_RESOLVE`:** it is computed directly rather than inferred from the legal resolvents, because a double resolution often has no legal counterpart -- cancelling either pair alone can leave a tautology, which `resolve` filters, so the legal set is empty while the student's answer still looks like an ordinary clause. Found while writing the test, not after.

**Bug caught by my own test:** the fixture for "every resolvent `resolve` returns is accepted" originally resolved only into tautologies, so `resolve` returned `[]` and the test would have passed vacuously. The guard assertion written alongside it failed instead, and the fixture was replaced with one having two genuine, non-tautological pivots.

**Bucket-assignment bug caught by `tools/loc.py`:** `fol_step.py` matched `[core]`'s `backend/src/core/*.py` glob, so its 48 lines were charged to `core`, pushing it from 939 to **987 -- over its 940 ceiling**. HLD §18.16.2 specified `core_fol`. Fixed by listing the file in `[core_fol]`'s patterns AND in `[core]`'s exclude, the same two-sided mechanism `core_m2` and the other FOL modules already use; `test_every_source_file_is_measured_by_exactly_one_bucket` is what makes a one-sided edit fail.

**Budget:** `core_fol` 847 -> **895** (+48 for the module). Cap 849, ceiling 934 -- over cap, **39 lines under ceiling**, so the §18.16.5 prediction held and no new exception was needed. `core` back to 939, unchanged. No new bucket; the frozen bucket list stands.

**Final state:** `pytest backend/` -- 1176 passed, 1 skipped (was 1159), both hash seeds. `ruff check` + `format --check` clean. Function-length and complexity gates pass. Not committed, not pushed.

---

## §18.16 step 3a: the full input path -- parser + translation layer | 2026-11-02 | Claude Code (Sonnet 5)

**Files created:** none.
**Files modified:** `backend/src/core/fol_step.py` (parser added), `backend/src/app/render.py` (`resolve_typed_clause`), `backend/tests/test_fol_step.py`, `backend/tests/test_render_fol.py`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The student stopped Step 3 to ask an unscoped question: how does a student's typed answer become the `FolClause` object `check_fol_step` validates? It hadn't been designed. Investigated the propositional board's own path first (`ProveBoard.jsx` splits on whitespace into `resolvent: list[str]`; `core.logic.normalize_literal` parses each single-letter token) and confirmed it cannot be reused -- FOL literals carry predicate names and argument lists, not single letters, and the student's explicit instruction was formal clause notation (`¬Study(ravi) ∨ PassTheExam(ravi)`), not English through `fol_english.py` (that module parses whole paragraphs, a different grammar).

**The design question that mattered:** `_clause_variable_names` (render.py) assigns fresh display letters INDEPENDENTLY per clause -- clause A's "x" and clause B's "x" are usually different internal `Variable` objects. A naive parser treating a typed "x" as one global `Variable("x")` would silently merge two independent variables into one, an unsound comparison the student would never see. This forced a two-layer split, confirmed correct by the student before implementation:

  1. **`core.fol_step.parse_literal_text` / `parse_clause_text`** (core_fol) -- pure syntax only. Text to `(negated, predicate_name, raw_term_strings)`; raw term strings are NOT yet classified as Variable or Constant, because that classification needs render.py's naming, which core_fol does not own (HLD S18.14.2). Raises `FolAnswerSyntaxError(text)` with the offending text attached on anything malformed; semantic mismatches (wrong predicate, wrong arity) are deliberately NOT rejected here -- they surface honestly through `check_fol_step` as `NOT_COMPLEMENTARY`/`WRONG_RESOLVENT`.
  2. **`Renderer.resolve_typed_clause`** (render.py, api_cli) -- translates raw term strings into real `Variable`/`Constant` objects using clause A's then B's own `_clause_variable_names` map (case-insensitive on the display lookup only; predicate names are never case-folded). A token matching neither clause's own display map is a `Constant` -- never guessed as a variable it is not. This is the exact case the two-layer design exists to get right, and it is tested directly: the same display letter ("x") shown by two different clauses resolves to two different internal `Variable` objects.

**27 new tests total** (18 for the parser's accepted/rejected forms, 9 for the translation layer), all written before their implementation.

**Bug caught by the project's own architecture test, not by me:** `parse_clause_text` originally used a bare `text.strip()` to detect blank input. `test_no_core_module_normalizes_text_itself` (`test_normalisation.py`) exists precisely to keep text handling inside the four modules that own it (`english.py`, `facts.py`, `logic.py`, `fol_english.py`); every other core module is supposed to receive already-normalized text or use only the unflagged operations. Fixed by using `.split()` (unflagged, and already needed for blankness-checking) instead of `.strip()`, with `parse_literal_text`'s own per-piece whitespace stripping doing the rest. The guard caught a real architectural violation on its own.

**Pre-existing propositional gap found in passing, NOT fixed:** a malformed propositional literal (`normalize_literal` raising a bare `ValueError`) is not registered in `main.py`'s `STATUS` table, so it falls through to the generic `Exception` handler -- a 500 with no details, not a clean 400 with a message. Out of scope tonight (propositional engine is frozen; this predates all of tonight's FOL work). Flagged here so the new `fol_step` wiring (Step 3b) does not repeat it -- `FolAnswerSyntaxError` and `FolStepError` will be registered in `STATUS` properly when the API action is wired.

**Budget:** `core_fol` 895 -> **921** (+26 for the parser). Cap 849, ceiling 934 -- **13 lines under ceiling**. `api_cli` 1123 -> **1145** (+22 for the translation layer), inside the §18.16.6 standing exception; real number reported as required, not absorbed silently. `CORE TOTAL` 2190 -> 2216, over cap 2121, well under ceiling 2335.

**Final state:** `pytest backend/` -- 1206 passed, 1 skipped (was 1176), both hash seeds. `ruff check` + `format --check` clean. Not committed, not pushed.

---

## §18.16 step 3b: the API action, live-verified | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/api/main.py` (`_fol_step`, `_ACTIONS`), `backend/src/api/schemas.py` (`FolStepAction`), `backend/src/app/render.py` (`fol_clause_by_label`, `fol_clause_text`, `fol_step_outcome`, `fol_answer_error`, `_label_clauses` extraction), `backend/src/core/tutor.py` (transition wiring), `backend/tests/test_api.py`, `backend/tests/test_render_fol.py`, `backend/tests/test_tutor.py` (two guard assertions updated).

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Wire the parser and validator built in Step 3a into a real `/api/act` action, with the six messages.yaml entries written for student-facing tone (shown and approved before implementation), and prove live that none of the six outcomes can ever 500.

**A correction made and flagged before implementing, not after:** the student's instruction was to register all six new error paths in `STATUS` for a 4xx. Checking `main.py`'s own stated rule -- *"would this be true regardless of the student's answer? -> HTTP status. Is this itself the teaching content? -> 200 with a code"* -- against how propositional's own `Diagnosis`/`Code` values are handled (never exceptions, always `200 {code, message}` from `_step`) showed all six FOL codes belong in that same lane, not `STATUS`. Implemented as `200 {code, message}` for all six, matching the established pattern exactly; `UnknownClause` (a stale/tampered label) is the one genuinely structural case and is the one that raises, reusing the exact exception propositional's own `_step` already raises. This still fully satisfies the underlying concern -- no student input can reach the generic 500 handler -- confirmed by the live verification below.

**One new shared labeling helper**, not two independent ones: `fol_proof_trace` and the new `fol_clause_by_label` both now read from one `_label_clauses(result)` function. A second, independent labeling pass would risk assigning different labels to the same clause between what the student sees on the trace and what the step handler resolves their submitted label to -- exactly the kind of drift this project has fixed twice already tonight (the CNF pipeline delegation, the derivation-extraction single source).

**`tutor.py`: a genuine ceiling cross, stopped on and reported before proceeding.** Wiring `"fol_step"` into `TRANSITIONS` (plus `ACTIONS`/`_PROVING_ACTIONS`) is the minimum three one-line additions this table can be expressed in without hiding a transition from a reader -- `tutor.py`'s own stated design principle. This crossed `core`'s ceiling by exactly one line. Checked for simplification first: every other file in the bucket is the frozen propositional engine, explicitly off-limits for this work, so no safe reduction exists. Reported, not absorbed; the student approved a standing exception scoped to exactly this three-line change, not a general loosening.

**Invariant explicitly checked, not assumed, per the student's condition:** every propositional-engine test file (`test_cnf.py`, `test_english.py`, `test_english_robustness.py`, `test_logic.py`, `test_search.py`, `test_entail.py`, `test_facts.py`, `test_cli.py`, `test_bkt.py`, `test_relevance.py`) has zero `git diff` and all 396 of their tests pass. Two `test_tutor.py` assertions DID need updating -- an action-count literal and a hardcoded copy of the full `TRANSITIONS` dict -- both are shape-pinning guards on the transition table by their own stated design ("a test that reads the table it is checking agrees with it by construction"), never propositional behaviour. Flagged and held for explicit approval before touching, per the student's instruction, rather than updated and reported after the fact.

**Live verification -- real HTTP, real running `uvicorn`, from the browser's own console, not `pytest`'s in-process `TestClient`.** The interactive board (Step 4) does not exist yet, so there is no dedicated UI to click through; this is the strongest verification available before it does. All eight outcomes confirmed on the live server:

| Outcome | HTTP | code |
|---|---|---|
| malformed answer | 200 | `FOL_ANSWER_MALFORMED` |
| no shared complementary predicate | 200 | `FOL_STEP_NOT_COMPLEMENTARY` |
| shared predicate, no unifier | 200 | `FOL_STEP_NO_UNIFIER` |
| two pairs cancelled at once | 200 | `FOL_STEP_DOUBLE_RESOLVE` |
| MGU applied to resolved literals only | 200 | `FOL_STEP_SUBST_INCOMPLETE` |
| a legal step exists, this isn't one | 200 | `FOL_STEP_WRONG_RESOLVENT` |
| the correct resolvent | 200 | `VALID` |
| a stale/unknown clause label | 400 | `UNKNOWN_CLAUSE` |

**Bug found by this exercise, fixed before it reached a report:** my own first `DOUBLE_RESOLVE` verification script hit `422 SCHEMA_INVALID` -- not a 500, the invariant held -- because it looked up a clause by exact rendered text and the canonical literal ordering put `Lucky(ravi)` before `Student(ravi)`, so the lookup silently returned `undefined`, which `JSON.stringify` drops from the request body, producing a genuinely malformed request. Root cause was the throwaway script, not the implementation; the equivalent `pytest` fixture already used substring matching and was unaffected.

**Propositional board confirmed unaffected, both ways:** `git diff --stat` shows zero changes to `ProveBoard.jsx`, `Feedback.jsx`, `MasteryBars.jsx`, `StartScreen.jsx`, `Explanation.jsx`; and loaded live in the browser, the propositional board renders its full, unchanged shape -- clause cards, resolvent input, insert buttons, three hint levels, "Does not follow", symbol legend, clause-English sidebar.

**Budget:** `core_fol` and `api_cli` unchanged in shape (api_cli absorbed the handler/schema/render additions within its existing standing exception; real number in `tools/loc.py`). `core` crossed its ceiling by one line, now under a scoped standing exception (HLD S18.16.7). `frontend` untouched -- no UI exists yet.

**Final state:** `pytest backend/` -- 1222 passed, 1 skipped (was 1212), both hash seeds. `ruff check` + `format --check` clean. `npm run build` clean. Not committed, not pushed.

---

## §18.16 step 4: the interactive board, live-verified | 2026-11-02 | Claude Code (Sonnet 5)

**Files created:** `frontend/src/FolProveBoard.jsx`.
**Files modified:** `backend/src/api/main.py` (`_fol_board_labels`, `_fol_step`), `backend/src/api/schemas.py` (`FolStepAction.accepted`), `backend/tests/test_api.py` (board-state contract tests), `frontend/src/App.jsx`, `frontend/src/useSession.js`, `frontend/src/ReadFacts.jsx` (bug fix), `frontend/src/labels.js`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** Before any code, confirmed `data/messages.yaml`'s `fol_step:`/`fol_answer:` blocks were already fully populated (all six codes) and pasted two full live JSON responses (code + message together) proving it -- `FOL_STEP_NOT_COMPLEMENTARY` and `FOL_STEP_WRONG_RESOLVENT`, the two given extra wording care. One red herring caught and ruled out before reporting: the first live capture showed a mangled `fol_reading` field (`âˆ€x` instead of `∀x`); traced to my own `curl | python -c "print(...)"` shell pipeline's console encoding, not the server -- confirmed with a clean end-to-end `urllib` script writing UTF-8 directly to a file, which came back correct.

**Checked whether `frontend`/`api_cli` had new simplification beyond §18.16.6, as instructed, rather than re-litigating settled ground:** both buckets measured byte-identical to their post-Step-3b figures (frontend 1005, api_cli 1212) -- nothing had touched either since. Reported that explicitly and skipped straight to Step 4 rather than re-auditing a question already closed.

**Stopped before writing the board itself** to flag a real design gap: `_fol_step` (Step 3b) validates one step against a FIXED original legend and does not persist anything, so a student's own chosen derivation path (which does not have to match the engine's single precomputed minimal derivation) has no stable label to refer to on a second request. Confirmed this concretely: resolving F1+F2 by hand produced `Mortal(socrates)`, a clause with no label anywhere, while the engine's own path resolves F1+F3 first. Presented the gap and a proposed fix; the student approved building it, with four explicit conditions.

**All four conditions addressed, each resolved before implementation, not during:**
1. **Bucket:** the accepted-clause list lives on the action (`FolStepAction.accepted`), never on `State` -- confirmed `core_session` was at its own ceiling (191/191, zero headroom) before deciding this, so neither `core` nor `core_session` gained a field.
2. **Ties into the existing machine:** `state.solved`/`stage="explain"` set the same direct way propositional's own `session.record_clause` already does (not a `tutor.TRANSITIONS` lookup), reusing the pre-existing `AlreadyFinished` 409 lock unmodified.
3. **Retry/undo parity:** confirmed `ProveBoard.jsx` has no granular undo before claiming parity -- the FOL board doesn't either, and invalid steps already never mutate state.
4. **Malformed state asserts:** reuses the existing `Tampered` exception (zero new exception types), raised when a stored `accepted` entry fails to reparse.

One documented limitation stated rather than hidden: a replayed clause loses its original variable-naming context, so a genuine surviving free variable becomes a constant on replay -- can only make a later step too strict, never unsound, and no worked example tonight exercises the case.

**Two real bugs found by actually using the board, neither caught by reading code:**
1. The board's initial clause list used the FULL `fol_trace.legend`, which includes the engine's own solution-path clauses, pre-labeled -- handing the student the answer before they did anything. Fixed by showing only `origin !== "derived"` entries initially; numbering still continues from the full legend length, so the visible sequence has an honest gap rather than a silently wrong one.
2. An earlier Phase 1 fix (hiding the Facts panel in FOL mode) had hidden the confirm-facts button in the same conditional -- no FOL session could ever leave the Facts screen at all. Fixed by splitting the confirm action out from the merge-specific UI it was wrongly bundled with.

**Live verification, browser, both modes, a complete two-step proof driven end to end:** a wrong resolvent (`Mortal(plato)`) refused with the board unchanged; the correct first step (`Mortal(socrates)` from F1+F2) accepted and rendered as `F6`, continuing past the hidden F4/F5; the second step (F6+F3 -> `□`) completing the proof; `state.solved` firing App.jsx's pre-existing `useEffect([stage])` auto-navigation to the Explanation tab with zero new navigation code written. The propositional board was then re-driven through its own full flow in the same session and confirmed unchanged: clause cards, per-symbol insert buttons, "Edit facts", both sidebars.

**Budget, `frontend` reported on its own, not folded into §18.16.6's number, as instructed:**

| file | code lines |
|---|---|
| `App.jsx` | 255 |
| `FolProveBoard.jsx` (new) | 127 |
| `FolExplanation.jsx` | 73 |
| `useSession.js` | 144 |
| `ReadFacts.jsx` | 147 |
| `labels.js` | 94 |

`frontend` **1005 -> 1242 (+237)**, already under the §18.16.6 standing exception; real number reported, not absorbed. `api_cli` **1212 -> 1228 (+16, measured before the frontend work started)** for the board-state backend logic -- `core`, `core_session`, `core_fol` all unchanged.

**Final state:** `pytest backend/` -- 1227 passed, 1 skipped (was 1222), both hash seeds. `ruff check` + `format --check` clean. `npm run build` clean. Not committed, not pushed.

---

## §18.16 step 5: the two-level hint ladder, live-verified | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/app/render.py` (`fol_unifier_text`, `fol_step_hint`), `backend/src/app/data.py` (`SUPPLIED["hint"]`), `backend/src/api/main.py` (`_fol_step_hint`, `_hint`), `backend/src/api/schemas.py` (`HintAction.accepted`), `data/messages.yaml` (`HINT_FOL_STEP_1/2/UNAVAILABLE`), `backend/tests/test_api.py`, `backend/tests/test_render_fol.py`, `frontend/src/App.jsx`, `frontend/src/Feedback.jsx`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02: every change across tonight's session came from Claude Code; nothing was hand-edited.

**Purpose:** The hint ladder from HLD §18.16.3, reopened as the explicit, stated reason for building FOL interactivity at all, and the one piece missing from Step 4.

**Three pre-items answered before any code**, per explicit instruction, none skipped:
1. Retry/undo on an accepted-but-dead-end step -- checked directly (not inferred): neither board has granular undo; a valid-but-useless clause is harmless clutter on both, matching propositional exactly.
2. The Step 4 frontend growth -- corrected the prior report's mischaracterization. §18.16.6 covered the state measured at that gate, not future growth. Checked for a real extraction (the two-clause picker, duplicated ~8 lines between the two boards) and declined it specifically because it would require editing `ProveBoard.jsx`, the one file every gate tonight has verified untouched -- not worth that risk for single digits of savings. Step 4's growth stands as its own exception.
3. Confirmed exactly what stops the board pre-showing solution clauses: a filter on `entry.origin !== "derived"`, restated precisely rather than re-asserted.

**Design, contract before code:** which step is hinted is keyed by `len(accepted)`, not `action.level` or `state.hint_level` -- the student's own derivation progress selects the target; the level controls only how much detail about that one target is revealed.

**A real design gap found and resolved during the contract, not left implicit:** a student's valid path can diverge from the engine's own canonical derivation (demonstrated directly in Step 4). `_fol_step_hint` checks whether the canonical next step's two parents are visible on the student's current board; if not, it returns a new, honest `HINT_FOL_STEP_UNAVAILABLE` message rather than silently falling back to wording that would actively mislead a student who already derived something correct (`HINT_FOL_FOLLOWS_1`'s "check your assumption it doesn't follow" makes no sense to someone who just proved a step).

**A real startup-contract catch, not a bug in my own logic:** `app/data.py`'s `SUPPLIED` registry rejected my first draft outright -- the two new hint templates used `{clause_a}`/`{clause_b}`/`{unifier}`, not registered as names the `hint` group supplies. This is the exact mechanism working as designed (catching a template/renderer mismatch at startup, before a student could ever see a crash); fixed by registering the three names.

**One real pre-existing test updated, not reverted:** `test_hint_tells_the_student_a_proved_fol_argument_follows` asserted the OLD outcome-level code for a case where a real derivation exists -- the exact case step-level hints are now DESIGNED to take priority on. Renamed and re-asserted to the new, correct, intended behavior; the budget-exhausted fallback (a genuinely separate test) was untouched and still passes.

**Two real frontend gaps found only by running it, neither visible from the backend suite:** `onHint` never sent `action.accepted`, so every hint silently acted as if nothing had been derived regardless of actual progress; `Feedback.jsx`'s tone map did not know the three new codes, so a correct hint would have rendered in the "bad" (red) error style. Both fixed -- both purely additive changes to shared components (new dict keys, one new argument on an existing call), confirmed safe by re-verifying the propositional board immediately after.

**Live verification, browser, both paths:** on a fresh board, Hint 1 named the engine's own canonical first step (F1+F3); Hint 2 added the unifier (`where x = socrates`). After deriving a different, equally valid first step (F1+F2 -> `Mortal(socrates)`, not matching the canonical path), Hint 1 correctly returned the honest `HINT_FOL_STEP_UNAVAILABLE` message rather than a misleading verdict restatement. Propositional hints re-verified immediately after and found unchanged (`HINT_1 start from c2.`, "Hint 1/2/3 of 3" labels intact).

**Budget:** `core`, `core_session`, `core_fol` all unchanged -- zero new lines in any of them, by design (everything reuses `_fol_board_labels`, `parse_clause_text`, `resolve_typed_clause`, `_fol_unifier_text`, none of which needed to grow). `api_cli` 1228 -> 1267 (+39). `frontend` 1242 -> 1247 (+5, the two wiring fixes only -- no new UI surface this step).

**Final state:** `pytest backend/` -- 1238 passed, 1 skipped (was 1227), both hash seeds. `ruff check` + `format --check` clean. `npm run build` clean. Not committed, not pushed.

---

## Deferred item: clause-English half of the Vocabulary sidebar | 2026-11-02 | Claude Code (Sonnet 5)

**Decision, not an implementation:** the student asked for propositional's Prove-board sidebar ("What the letters mean" / "What each clause says") to be matched for FOL. The request splits into two independently-sized pieces, and only one is being built.

**"What the letters mean" (predicate/constant -> English) -- in scope, proceeding as its own gate.** Directly buildable: the registry mapping (written word -> predicate/constant) is already computed during FOL parsing and currently discarded.

**"What each clause says" (clause -> English prose) -- deferred, not built, logged so it is not silently dropped.** No FOL equivalent to `core.narrate`/the propositional `clauseEnglish` map exists. Building one would be new translation logic -- generating English prose FROM a post-CNF FOL clause, including handling Skolem terms, which HLD §18.15.4 already named out of scope for exactly this reason ("Skolem-term English naming... out of scope; the raw term plus the footnote is the whole treatment"). This is a design change, not an extension of existing rendering, and needs its own HLD gate before any code -- not something to fold into the predicate/constant legend work.

---

## Correctness fix: verb + bare plural object | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/core/fol_english.py`, `backend/tests/test_fol_english.py`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02.

**Purpose:** Found live while investigating a reported fallback bug: "Aisha solves problems" (no "the") silently parsed as `Solve(aisha, problems)`, treating the common noun "problems" as a second individual -- a wrong answer, not a refusal. Fixed by reusing the existing `_canonical_word` regular-plural detector as a second signal alongside the existing determiner check: the LAST word of the remaining tokens being a regular plural routes to the unary verb+object reading, same as `"the"` already does. Checked the existing test suite for regression risk before writing: no ground-relation test's second individual (`Bob`, `Carol`, `Dave`) is a regular plural, so nothing was at risk of breaking, confirmed by the full suite staying green.

**Known, accepted limitation, stated explicitly:** a proper name that happens to be a regular plural form (ending in "-s" the way `_canonical_word` strips) is misread as an object noun. Same risk already accepted for `_canonical_word` itself earlier tonight -- not a new standard, not silently introduced.

**Budget:** `core_fol` code lines unchanged (921 -- one existing condition extended, no new lines), still under cap.

**Final state:** `pytest backend/` -- 1242 passed, 1 skipped (was 1238), both hash seeds. `ruff check` + `format --check` clean. Not committed, not pushed.

---

## Fix: detect_mode on lexical quantifier presence | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/core/fol_english.py` (`_has_quantifier_word`, `is_fol_sentence`), `backend/tests/test_fol_english.py`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02.

**Purpose:** Found live: a paragraph containing a genuinely FOL-intended but currently-unparseable sentence ("All engineers solve problems" -- no copula, no relative clause) fell through to full propositional treatment, including the relevance banner, because `detect_mode` depended on a SUCCESSFUL FOL parse rather than the lexical presence of a quantifier word. Fixed in `fol_english.py` alone: `is_fol_sentence` now signals FOL mode on lexical quantifier presence even when this grammar's narrower patterns cannot parse the sentence. Safe by construction -- confirmed, not assumed -- because `core.english`'s own grammar refuses every quantifier word unconditionally, so no sentence propositional would otherwise have accepted can be taken away by this change.

**No `session.py` change needed, confirmed before writing anything there:** `core_session` is at zero headroom (191/191), so this mattered. §18.16's own earlier Phase 1 fix already suppresses `warnings` unconditionally whenever `logic_mode == "fol"` -- the one `fol_english.py` change was sufficient on its own to stop the misleading fallback.

**What was NOT achieved, stated rather than silently claimed as complete:** the per-sentence refusal still shows the bare code, not FOL-flavored prose. Checked precisely: `Renderer.error()` (the method that renders a code's messages.yaml wording, rephrasing hint included) is called only from the CLI -- the web UI shows the bare `error_code` string for every sentence refusal today, propositional or FOL, a pre-existing gap unrelated to tonight's work. Building and wiring FOL-specific web prose is its own, larger, unscoped item -- logged here, not attempted.

**Live-verified, both the direct pipeline and the real running server**, on the reported paragraph (now `logic_mode: fol`, `warnings: []`) and all three previously-confirmed worked examples (Ravi, Socrates, Tweety -- all unchanged), plus a genuinely-unsupported multiply-quantified paragraph (still cleanly refuses, never starts succeeding at nonsense).

**Budget:** `core_fol` 921 -> 924 (+3), still under cap, 10 lines to ceiling. `core`/`core_session`/`api_cli`/`frontend` untouched.

**Final state:** `pytest backend/` -- 1248 passed, 1 skipped (was 1242), both hash seeds. `ruff check` + `format --check` clean. Not committed, not pushed.

---

## Grammar addition: bare "All SUBJECT verb OBJECT" quantified pattern | 2026-11-02 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/core/fol_english.py` (`_parse_all_bare_svo`), `backend/tests/test_fol_english.py`.

**What the student changed by hand:** none -- confirmed directly with the student, 2026-11-02.

**Purpose:** The remaining piece of the reported paragraph: "All engineers solve problems" has no copula and no relative clause, a genuine gap in every previously-supported quantified pattern. Added as its own scoped grammar addition, same discipline as every other extension tonight -- contract first (exact accepted syntax, how it composes with the verb+object fix), tests first, then implementation.

**Reuses, does not re-derive, the signal from the earlier correctness fix tonight:** the object phrase must carry a determiner or end in a regular plural -- the exact rule `_parse_ground`'s own verb+object branch already uses, so the quantified and ground forms of the same pattern can never disagree about what counts as an object phrase. A quantified relation to a named individual ("All engineers like Bob") is deliberately still refused -- the same structural ambiguity the ground pattern accepts and never guesses at, not newly claimed as supported.

**One of my own earlier tests needed updating, expected consequence not a regression:** item 2's "genuinely unsupported quantifier sentence" regression test used "All engineers solve problems" as its negative example -- which this item deliberately made supported. Swapped for a multiply-quantified relation ("All engineers like every manager"), explicitly out of scope before and after every fix tonight.

**Live-verified end to end on the real running server**, the exact reported paragraph: `logic_mode: fol`, `warnings: []`, all three sentences read correctly (`∀x (Engineer(x) → SolveProblem(x))`, `Engineer(aisha)`, `SolveProblem(aisha)`), and the argument **proves**: `"Valid -- the empty clause was derived in 2 step(s)."`

**Budget, flagged explicitly:** `core_fol` landed at exactly its ceiling -- zero headroom remains for any further FOL engine work without a simplification pass or a recorded exception. Not a crossed ceiling (no stop triggered), but the very next line added to any of the six `core_fol` files will cross it.

**Final state:** `pytest backend/` -- 1255 passed, 1 skipped (was 1248), both hash seeds. `ruff check` + `format --check` clean. Not committed, not pushed.

---

## Web error-prose wiring: `Renderer.sentence_errors` | 2026-11-03 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/app/render.py` (`sentence_errors`), `backend/src/api/main.py` (all eight `clause_english` response sites), `backend/tests/test_render.py`, `backend/tests/test_api.py`, `frontend/src/useSession.js`, `frontend/src/ReadFacts.jsx`, `frontend/src/App.jsx`.

**What the student changed by hand:** none -- confirmed directly with the student.

**Purpose:** Closed the gap logged two entries above: the web UI showed a refused sentence's bare error code (e.g. `QUANTIFIER_UNSUPPORTED`) with no rephrasing hint, while the CLI already rendered it through `Renderer.error()`. `sentence_errors(sentences)` reuses `error()` and the existing `error:` `messages.yaml` section verbatim -- no new wording, for propositional and FOL refusals alike, since `SentenceRec.error_code` is always one of `core.english`'s own codes regardless of `logic_mode`.

**Bucket confirmed before writing:** `api_cli` only (new response key on an endpoint that declares no `response_model`, mirroring exactly how `clause_english` already works) -- zero `core`/`core_fol`/`core_session` touch.

**Live-verified end to end in the real browser**, both modes, on the exact reported sentence (`"It rains. It rains and it is cold or it is windy."`): the Facts screen now shows *"mixing \"and\" with \"or\" in one sentence is ambiguous. Split it into two sentences."* next to the refused sentence, in a propositional session and inside an otherwise FOL-mode session alike -- not the bare code.

**Final state:** `pytest backend/` -- 1262 passed, 1 skipped, both hash seeds. `ruff check` + `format --check` clean (also cleaned two pre-existing lint defects in `test_render.py` left over from the prior block: an import not at top of file, a line over 100 chars). Frontend build clean. Not committed, not pushed.

---

## Bug fix: FOL session with a quantified conclusion stuck on Read & Facts | 2026-11-03 | Claude Code (Sonnet 5)

**Files modified:** `backend/src/core/session.py` (`state_of`'s stage derivation, one line), `backend/tests/test_api.py`, `frontend/src/useSession.js` (`goHome` -- separate bug, see below).

**What the student changed by hand:** none -- confirmed directly with the student.

**Found live, not reported by the student:** while live-verifying FOL rendering with a deliberately hard multi-quantifier paragraph ("All students who study pass. No teacher is a student. Some student studies." / "Some student passes." -- exercises `all...who`, `no`, and `some` together, independently confirmed `PROVED` in 4 steps), clicking "These facts are right -- start proving" failed with `400 WRONG_STAGE` every time.

**Root cause, read off the code, not guessed:** `state_of` (session.py) set `stage="read" if found.entailment is None else "facts"` -- it only ever consulted the PROPOSITIONAL entailment. `core.english`'s grammar refuses any sentence containing a quantifier word unconditionally, regardless of FOL mode, so whenever the CONCLUSION sentence itself is quantified, the propositional parse of the conclusion fails, `entailment` is `None`, and the session is permanently stuck at `stage="read"` -- `tutor.TRANSITIONS` has no `("read", "confirm_facts")` row. Every FOL paragraph tested before tonight happened to use a ground, unquantified conclusion ("Socrates is mortal."), which is why this went unnoticed: this bug affects any FOL exercise whose goal itself uses "every"/"all"/"some"/"no".

**The fix is the general rule, not a narrower patch:** `stage="read" if found.entailment is None and found.fol_result is None else "facts"` -- reads `found.fol_result`, which `analyse()` already computes generically for any paragraph whenever `logic_mode == "fol"`. No sentence-matching, no quantifier/predicate-word checks, no new logic -- strictly reading an already-computed value, same spirit as the `detect_mode` fix two entries above.

**Budget, checked before writing:** `core_session` was at zero headroom (191/191, flagged explicitly by the student before authorizing this fix). Checked for a genuine simplification elsewhere in the file first; none needed -- the fix extends an existing line's condition rather than adding a new one, so `core_session` stayed at exactly 191/191, no exception required.

**Separate bug found and fixed in the same pass:** `goHome` (`useSession.js`) cleared `state`/`feedback`/`warnings`/`clauseEnglish`/`sentenceErrors` but never `problem` -- so after any `ApiError` (this `WRONG_STAGE`, or any other), clicking "New argument" left the old error banner showing over the fresh start screen until the next submit. Added `setProblem(null)` to `goHome`.

**Regression confirmed, not assumed:** a propositional-only session (`fol_result` always `None`) still reaches `"facts"` exactly as before -- the condition now reads `fol_result` ALONGSIDE `entailment`, never instead of it. New test asserts this explicitly.

**Live-verified end to end in the real browser** on the exact paragraph above: Read & Facts shows the three readings cleanly, clicking "These facts are right -- start proving" now returns `FACTS_CONFIRMED` and reaches the Prove board with the five expected clauses (F1-F5) -- no `WRONG_STAGE`. (First two browser attempts still showed the error because the running `uvicorn` process predated the fix and was not using `--reload`; restarting it was the actual fix, not a second code change.)

**Final state:** `pytest` (repo root and `backend/`) -- 1262 passed, 1 skipped, both hash seeds. `ruff check` + `format --check` clean. `python tools/loc.py` -- `core_session` unchanged at 191/191; no bucket newly crossed a ceiling. Frontend build clean. Not committed, not pushed.

**Deferred, not attempted tonight -- named explicitly so it is not silently dropped:**
1. **The broader pattern this bug is one instance of:** several propositional-only code paths were written before FOL mode existed and were never audited for whether they still make sense when `logic_mode == "fol"`. `state_of`'s stage derivation was one; there may be others (anything that branches on `entailment`/`relevant_ids`/propositional-only fields without also checking `fol_result`). Not audited tonight -- this is about speed under the submission deadline, not about tonight's fix being wrong.
2. **The dropdown-vs-auto-detect question:** whether `logic_mode` should stay auto-detected from lexical quantifier presence (current behavior) or become an explicit student-facing choice, is unresolved and was not decided tonight.
3. **A second, independently-discovered bug, confirmed but NOT fixed -- reported to the student instead of patched:** `Renderer.resolve_typed_clause` (`app/render.py`) unconditionally lowercases any typed token that isn't a recognized clause variable name into `Constant(token.lower())`. A Skolem constant is displayed on the board with an uppercase label (e.g. `C1`, confirmed `Constant(name='C1')`), so a student typing that exact label back -- the only thing the UI shows them to reference it by -- gets compared against `Constant(name='c1')` and is wrongly told `FOL_STEP_WRONG_RESOLVENT` for a textbook-correct step. Confirmed with a direct `Constant("C1") == Constant("c1")` check (`False`) and reproduced live in the browser on the exact multi-quantifier paragraph above. Not fixed: the correct fix likely needs case-insensitive matching against constants ALREADY appearing in clauses `a`/`b` (mirroring the existing variable-name lookup), not a blanket case change, since named individuals ("Socrates") may rely on the current lowercasing elsewhere -- needs its own careful check before touching `app/render.py` again.
