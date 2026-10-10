# Mutation testing log

Test-quality evidence. A passing suite proves nothing on its own, so after each module the
implementation is deliberately broken and the suite re-run. A mutation that survives means the
tests cannot see that defect.

Facts only: every row is an injected change and the observed pytest result. No claim is made
beyond the counts.

Method: inject one defect **into an isolated `git worktree` at HEAD**, run `python -m pytest`,
record the result, discard the worktree. `backend/src` is never written to — see "Isolation" below
for the two incidents that forced that design. Machine: Intel64 / Windows 11 / CPython 3.12.10.

---

## `core/logic.py` — Phase 2 (2026-10-08)

Suite at the time: 38 tests.

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| M1 | Diagnosis order: DOUBLE_CANCEL moved after WRONG_RESOLVENT | yes | 5 |
| M2 | TAUTOLOGY check removed | yes | 1 |
| M3 | DUPLICATE check removed | yes | 1 |
| M4 | Double-cancel accepts a single pair | yes | 1 |
| M5 | `normalize_literal` drops `.upper()` | yes | 5 |
| M6 | `resolvents` keeps the pivot in `b` | yes | 10 |
| M7 | `missing`/`extra` swapped | yes | 1 |
| M8 | `canonical()` returns an unsorted tuple | **NO** | 0 |

**Score: 7/8.**

**M8 survivor analysis.** The ordering test compared two frozensets built in different orders.
Equal frozensets iterate identically within one process, so the assertion held for any
implementation. Fixed by asserting the output *is* sorted, over eight literals. Re-verified
under `PYTHONHASHSEED` 0, 4242 and 99: fails in all three.

**Score after fix: 8/8.**

---

## `core/search.py` — Phase 3 (2026-10-08)

Suite at the time: 56 tests.

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| S1 | `successors` allows tautologies | yes | 1 |
| S2 | Resolvents of a pair iterated unsorted | **NO** | 0 |
| S3 | Clauses iterated unsorted (hash order) | **NO** | 0 |
| S4 | Cache stores cap hits | yes | 1 |
| S5 | Exhaustion returns `None` instead of raising | yes | 1 |
| S6 | `productive` accepts any distance drop | yes | 1 |
| S7 | `best_next_step` returns the first legal step | **NO** | 0 |
| S8 | `fallback_step` ignores clause length | **NO** | 0 |

**Score: 4/8.**

**Survivor analysis.**

- **S3** — same defect class as M8: the ordering test rebuilt a set and compared it with itself.
  Fixed by asserting the emitted order is canonically sorted.
- **S7** — in every fixture the canonically first legal step happened to be the correct one.
  Added `DISTRACTOR_FIRST`, where the first legal step is a dead end.
- **S8** — in every fixture the first clause pair happened to contain a unit clause. Added
  `UNIT_SORTS_LAST`, where the unit clause sorts last.
- **S2** — **not a test gap.** A clause pair yields at most one legal resolvent: one pivot gives
  exactly one resolvent, and two or more pivots make every resolvent a tautology, which is
  filtered. Checked by sampling 202,223 random non-tautological clause pairs over six symbols:
  the maximum number of legal resolvents from any single pair was **1**. The sort is therefore
  unobservable and was kept deliberately as a local determinism guard, with
  `test_a_clause_pair_offers_at_most_one_legal_step` pinning the property.

**Score after fixes: 7/8, with the eighth shown to be unobservable.**

---

## `core/english.py` — Phase 4a (2026-10-08)

### First pass — suite of 97 tests

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| E1 | `"if"` scanned before `"if and only if"` | yes | 3 |
| E2 | `"B if A"` direction reversed | yes | 3 |
| E3 | `"only if"` direction reversed | yes | 2 |
| E4 | `unless` produces AND instead of OR | yes | 2 |
| E5 | Mixed and/or silently allowed | yes | 1 |
| E6 | Quantifier check removed | yes | 7 |
| E7 | `TOO_LONG` off by one | yes | 1 |
| E8 | `neither` does not negate its clauses | yes | 4 |
| E9 | Double negation stacks instead of cancelling | yes | 1 |
| E10 | `either` no longer forces a disjunction | **NO** | 0 |
| E11 | Sentence-initial `only if` accepted | yes | 1 |
| E12 | Empty fact phrase allowed | yes | 1 |
| E13 | Consequent truncated to its first clause | yes | 1 |

**Score: 12/13.**

**E10 survivor analysis.** The ambiguity test only covered sentences mixing *both* connectives,
which the generic check still rejects. The uncovered case is a sentence such as
*"Either it rains and it is cold"*: only one connective is present, so it would have parsed as a
**conjunction** — the opposite of what *either* promises — with nothing downstream able to
detect it. Tests added for that case and its `both` counterpart.

While tracing E10 a second defect surfaced that no mutation had targeted: the grammar writes
`("or" clause)+`, but the parser accepted *"Either it rains"* and demoted it to a bare clause.
The first fix rejected it outright, which **regressed** *"Both lights are on"* — a legitimate
fact. Final rule: a prefix brackets only when the connective it governs is present; the opposite
connective is `AMBIGUOUS_AND_OR`; otherwise the word is ordinary phrase content.

### Second pass — after the B2–B6 robustness work, suite of 153 tests

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| E1–E9, E11–E13 | as above | yes | 1–14 each |
| E10 | `either` no longer forces a disjunction | **NO** | 0 |
| E14 | Prefix-governs-wrong-connective guard removed | yes | 1 |
| E15 | Unicode folding skipped before lowercasing | yes | 7 |
| E16 | Decimal-point guard removed from the splitter | **NO** | 0 |
| E17 | Splitter breaks at every terminator | yes | 1 |
| E18 | Compound indefinites removed from the quantifier list | yes | 3 |
| E19 | `neither … nor` branch disabled | yes | 4 |

**Score: 17/19.**

**Both survivors were redundant code, not test gaps**, and both were removed:

- **E10** — once the E14 guard existed, the `forced` parameter on `_junction` could no longer
  change any outcome: the wrong-connective case is intercepted before `_junction` is called, and
  the mixed case is caught by the generic check. The parameter was deleted.
- **E16** — the decimal-point special case was subsumed by the uppercase rule, because a digit is
  not uppercase. The branch was deleted and the reasoning recorded in the docstring.

### Third pass — after removing the redundant code

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| E20 | Mixed-connective check removed | yes | 1 |
| E21 | Splitter breaks at every terminator | yes | 3 |
| E14b | Prefix-governs-wrong-connective guard removed | yes | 1 |
| E22 | Prefix branch never taken | yes | 5 |

**Score: 19/19 observable defects caught, with no redundant code left for a mutation to hide in.**

---

## Running total

| Module | Observable defects injected | Caught | Unobservable (proved) |
|---|---|---|---|
| `logic.py` | 8 | 8 | 0 |
| `search.py` | 7 | 7 | 1 |
| `english.py` | 19 | 19 | 0 |
| **Total** | **34** | **34** | **1** |

Four defects that initially survived were fixed by strengthening tests; two were fixed by
deleting code the mutation showed could not matter; one was proved unobservable by sampling.

---

## `core/facts.py` — Phase 4b (2026-10-08)

Suite at the time: 266 tests.

| ID | Injected defect | Caught? | Failures |
|---|---|---|---|
| F1 | Suffix step removed | yes | 45 |
| F2 | Drop-trailing-`e` removed | yes | 5 |
| F3 | Doubled-consonant collapse removed | yes | 10 |
| F4 | `ss` no longer protected from collapse | yes | 1 |
| F5 | `y→i` ignores the consonant condition | yes | 1 |
| F6 | `y→i` removed | yes | 8 |
| F7 | Fixpoint reduced to a single pass | yes | 5 |
| F8 | Minimum-stem guard removed | **NO** | 0 |
| F9 | `ies→i` rule removed | **NO** | 0 |
| F10 | Polarity parity inverted (any negation ⇒ negative) | yes | 1 |
| F11 | Negation tokens left in the canonical key | yes | 1 |
| F12 | Empty-key check removed | yes | 1 |
| F13 | Key made order-insensitive | *(invalid mutation — syntax error, not scored)* | — |
| F14 | `opposite` no longer flips polarity | yes | 1 |
| F15 | `different` no longer splits a group | yes | 2 |
| F16 | Self-merge check removed | yes | 1 |
| F17 | Unknown-phrase check removed | yes | 1 |
| F18 | Conflict detection removed | yes | 2 |
| F19 | Conflict keyed on the ordered pair | yes | 1 |
| F20 | Fact limit enforced even when `enforce_limit` is false | yes | 1 |

**Score: 17/19 scored mutants.**

**Survivor analysis.**

- **F9 — redundant code, deleted.** For any word ending in `ies`, stripping `es` leaves exactly
  what `ies→i` produces (`studies → studi` either way), so the rule could never change an
  outcome. Removed rather than left looking meaningful.
- **F8 — a real test gap, closed.** No test reached a word short enough for the guard to matter.
  Without it the fixpoint eats short words whole: `see → se → s → ""`, and every such word would
  then share the empty key and become one fact. The existing `sees`/`see` pair could not detect
  it because both collapsed to `""` and therefore still matched. Added
  `test_minimum_stem_guard_stops_short_words_vanishing`, which asserts `stem("see") == "se"` and
  that no stem is shorter than two characters.

**Score after fixes: 18/18 remaining mutants caught** (F9's code no longer exists to mutate).

### Defect found by the `loc.py` tests, not by mutation

`measure()` counted each bucket independently, so a blank line **inside** a docstring was counted
twice and subtracted twice — **undercounting code and silently inflating the budget allowance**.
Rewritten to label every line exactly once, docstring first, so the four buckets always sum to
the total. Pinned by `test_measure_counts_every_line_exactly_once`.

## Running total

| Module | Scored mutants | Caught | Unobservable (proved) | Redundant code deleted |
|---|---|---|---|---|
| `logic.py` | 8 | 8 | 0 | 0 |
| `search.py` | 7 | 7 | 1 | 0 |
| `english.py` | 19 | 19 | 0 | 2 |
| `facts.py` | 18 | 18 | 0 | 1 |
| **Total** | **52** | **52** | **1** | **3** |

---

## `core/cnf.py` — Phase 4c (2026-10-08)

Suite at the time: 309 tests.

**Method change.** The first run was driven from a shell loop, and the "distribution direction
flipped" mutant sent `distribute` into unbounded recursion. The loop timed out and left the file
mutated — with no committed copy to restore from, because the module was still untracked. The
driver was rewritten in Python with a per-mutant timeout and a `git checkout` restore in a
`finally` block, and the module is now committed before any mutation run. A hang is recorded as
*caught*, since a non-terminating conversion is a defect the suite surfaced.

| ID | Injected defect | Caught? |
|---|---|---|
| C1 | `Implies` loses its negation | yes |
| C2 | `Iff` keeps only one direction | yes |
| C3 | `Iff` joins with Or instead of And | yes |
| C4 | De Morgan: ¬(A∧B) yields And | yes |
| C5 | De Morgan: ¬(A∨B) yields Or | yes |
| C6 | Double negation stacks instead of cancelling | yes |
| C7 | Distribution direction flipped | yes *(hung — unbounded recursion)* |
| C8 | Distribution skipped entirely | yes |
| C9 | Tautology removal disabled | yes |
| C10 | Duplicate removal disabled | yes |
| C11 | Clauses returned unsorted | **NO** → fixed |
| C12 | Goal is not negated | yes |
| C13 | `_flatten` ignores nesting | **NO** → code deleted |
| C14 | A negative `literal_of` no longer cancels the `Not` | yes |
| C15 | `distribute` drops its single-operand unwrap | **NO** → fixed |

**Score: 12/14 first pass → 15/15 after the fixes.**

**Survivor analysis.**

- **C11 — test gap.** Sortedness was asserted on a two-clause result, which can come out ordered
  by luck, and determinism was checked by calling twice *in one process*, where equal sets
  iterate identically. Re-pointed at the 25-clause worst case.
- **C13 — redundant code, deleted.** `distribute` rebuilds bottom-up and flattens as it goes, so
  the helper never sees an operand of its own kind; the recursion could not change any outcome.
  Reduced to a one-level `_parts` with the reasoning recorded in its docstring.
- **C15 — test gap.** `distribute` unwraps a one-item And/Or, which is a real normalisation
  contract (callers may match on node type without peeling wrappers) but was never asserted,
  because the parser cannot build a one-item junction. Pinned by a direct call.

## Running total

| Module | Scored mutants | Caught | Unobservable (proved) | Redundant code deleted |
|---|---|---|---|---|
| `logic.py` | 8 | 8 | 0 | 0 |
| `search.py` | 7 | 7 | 1 | 0 |
| `english.py` | 19 | 19 | 0 | 2 |
| `facts.py` | 18 | 18 | 0 | 1 |
| `cnf.py` | 15 | 15 | 0 | 1 |
| **Total** | **67** | **67** | **1** | **4** |

---

## Regenerating these numbers

```
python scripts/mutate.py            # every module
python scripts/mutate.py cnf        # one module
```

Mutants live in `data/mutants.json`; the driver is `scripts/mutate.py`.

**Conventions, because they affect the score.** A mutant is *caught* when pytest exits non-zero.
A **timeout counts as caught**: a non-terminating conversion is a defect the suite surfaced, and
scoring it as a survivor would reward code that hangs over code that fails. A mutant whose anchor
text no longer exists is reported as **retired** — never silently skipped, and never scored.

**What is and is not reproducible.** The command regenerates the *current* score for every module.
The first-pass tables above are a record of what was found at the time and are deliberately not
re-runnable: several of those mutants targeted code that the findings themselves caused to be
deleted or rewritten, so their anchors are gone by construction.

### Full set on the committed code, 2026-10-08

| Module | Mutants | Caught |
|---|---|---|
| `cnf.py` | 15 | 15 |
| `english.py` | 10 | 10 |
| `facts.py` | 10 | 10 |
| `logic.py` | 7 | 7 |
| `search.py` | 6 | 6 |
| **Total** | **48** | **48** |

`C7` (distribution direction flipped) is the timeout case: it recurses without bound and is
counted as caught under the convention above.

---

## `core/entail.py` and `core/relevance.py` — Phase 5 (2026-10-09)

Run with the committed driver. Suite at the time: 336 tests.

| ID | Module | Injected defect | Caught? |
|---|---|---|---|
| N1 | entail | Consistency check removed | yes |
| N2 | entail | A clause read as a conjunction, not a disjunction | yes |
| N3 | entail | Negative literals evaluated with the wrong sign | yes |
| N4 | entail | Rows enumerated in reverse (counterexample becomes the last) | **NO** -> fixed |
| N5 | entail | Symbols returned unsorted | **NO** -> fixed |
| N6 | entail | Fact-count guard removed | yes |
| N7 | entail | Tautological-conclusion warning removed | yes |
| N8 | entail | `NOT_ENTAILED` reports no counterexample | yes |
| N9 | entail | The two verdicts swapped | yes |
| N10 | entail | The goal ignored when looking for a counterexample | yes |
| R1 | relevance | The inconsistency refusal removed | yes |
| R2 | relevance | Reachability not transitive (single pass) | yes |
| R3 | relevance | A kept clause no longer contributes its facts | yes |
| R4 | relevance | Kept and dropped swapped | yes |
| R5 | relevance | Output returned unsorted | yes |
| R6 | relevance | Search starts from nothing instead of the goal's facts | yes |
| R7 | relevance | A clause must contain ALL reached facts to be kept | yes |
| R8 | relevance | Everything kept regardless of reachability | yes |

**Score: 16/18 first pass -> 18/18 after the fixes.** `relevance.py` was 8/8 from the start.

**Survivor analysis — both were the same weakness, in two forms.**

- **N4** — the determinism test used cases with exactly **one** satisfying row, so "first" and
  "last" coincided and reversing the enumeration changed nothing. Replaced with a case having
  several satisfying rows, where counter order picks a specific one.
- **N5** — sortedness was asserted over three symbols, which can come out ordered by chance.
  Widened to eight and asserted against `sorted()` directly. Symbol order is load-bearing, not
  cosmetic: it fixes which bit each symbol occupies and therefore which row is reported.

### Second process failure, recorded

The driver restored the target with `git checkout`, which **silently fails on a file git does
not track**. Both new modules were untracked, so the restore did nothing and two files were left
mutated — the same outcome as the shell-loop failure in Phase 4c, from a different cause. The
driver now restores from an in-memory copy and **asserts the file matches** before the next
mutant runs; that has no precondition on version control.

## Running total

| Module | Scored mutants | Caught |
|---|---|---|
| `logic.py` | 7 | 7 |
| `search.py` | 6 | 6 |
| `english.py` | 10 | 10 |
| `facts.py` | 10 | 10 |
| `cnf.py` | 15 | 15 |
| `entail.py` | 10 | 10 |
| `relevance.py` | 8 | 8 |
| **Total** | **66** | **66** |

---

## Isolation — the third process failure, and the structural fix (v2.9 A1/A2, 2026-10-10)

Three runs in a row damaged the working tree, each from a different cause:

| # | Phase | Cause | Fix at the time |
|---|---|---|---|
| 1 | 4c | A shell loop timed out on `C7` (unbounded recursion) with no committed copy to restore from | Rewrote the driver in Python with a per-mutant timeout and a `git checkout` restore in `finally` |
| 2 | 5 | `git checkout` **silently succeeds on a file git does not track**. Both new modules were untracked, so the restore did nothing and two files were left mutated | Restore from an in-memory copy and assert the file matches |
| 3 | — | Restore-from-memory still *writes to the real file*. A crash between write and restore leaves a mutant on disk, and **a surviving mutant passes the tests by definition**, so a green suite is no evidence the files are clean | **Structural: never write to the real file at all** |

**The fix is structural, not another careful restore** (`scripts/mutate.py`):

1. mutations are applied only inside a **detached `git worktree` at HEAD** — a separate directory,
   so `backend/src` is never opened for writing. Using a worktree rather than a copy also means
   mutants always apply to **committed** content, so a stale editor buffer cannot reach a score;
2. the run **refuses to start** if the working tree is dirty or a target file is untracked — the
   exact precondition that failed in incident 2;
3. `backend/src` is **fingerprinted before and after** (paths *and* bytes, so a rename counts) and
   a difference aborts the run.

All three properties are asserted by `backend/tests/test_mutation_driver.py`, including that a
write inside the isolated checkout leaves `backend/src` byte-identical. The refusals are tested
against a throwaway repository, because dirtying this one to test the check would be the bug the
check exists to prevent.

### Incident verification — was the committed source actually clean?

A passing suite could not answer this, so every one of the 66 mutants was checked directly against
the **committed blob** (`git show HEAD:<module>`), not the working file. For each: the anchor text
must be **present** (absent ⇒ the mutation had been applied and the anchor eaten) and the
replacement text **absent**.

| Result | Count |
|---|---|
| Anchor present in the committed blob | **66 / 66** |
| Committed blob identical to the working tree | **66 / 66** |
| Replacement text absent | 57 / 66 |
| Replacement text present — **explained below, all legitimate** | 9 |

Plain substring matching reports a replacement as "present" whenever it is also a prefix of its own
anchor, or ordinary Python that occurs elsewhere. Each of the nine was traced to a specific line:

| ID | Replacement text | Why it legitimately appears |
|---|---|---|
| C15 | `return And(parts)` | A **prefix of its own anchor** on `cnf.py:77` (`return And(parts) if len(parts) > 1 else parts[0]`) |
| F8 | `return candidate` | A **prefix of its own anchor** on `facts.py:90` |
| S7 | `        return (a, b, resolvent)` | A **suffix-substring** of the more deeply indented anchor on `search.py:134`, and of `search.py:150` in `fallback_step` |
| C12 | `return to_clauses(node, literal_of)` | `cnf.py:118` is `premise_clauses`, which correctly does **not** negate. The anchor is `cnf.py:127` in `goal_clauses`, which must. The pair *is* the premise/goal asymmetry |
| C14 | `f"~{literal_of(...)}"` | `cnf.py:94` is the branch that negates a **positive** literal, which is correct. The anchor is `cnf.py:92`, the branch that strips `~` from a negative one. The mutant would collapse the two |
| E8 | `tuple(_clause(segment, …) …)` | `english.py:245` is the `and`/`or` grouping, where clauses must **not** be negated. The anchor is `english.py:299`, the `neither` branch, where they must |
| F3 | `return word` | An ordinary statement at `facts.py:97, 124, 126`; the anchor is line 106 |
| F14 | `pass` | The only occurrence is the English word inside a docstring — `facts.py:194`, "on the first **pass**". Not code at all |
| S8 | `key=canonical` | Ordinary determinism sorts at `search.py:51, 54, 148`; the anchor is line 146, the length-aware key |

**Conclusion: the committed source carried no mutation.** The two files left mutated in incident 2
were repaired before the Phase 5 commit; this check proves it rather than assuming it.

### Full set re-run on committed code under the hardened driver, 2026-10-10

Commit `fd56677`, suite of 342 tests, run inside the isolated worktree:

| Module | Mutants | Caught |
|---|---|---|
| `cnf.py` | 15 | 15 |
| `english.py` | 10 | 10 |
| `entail.py` | 10 | 10 |
| `facts.py` | 10 | 10 |
| `logic.py` | 7 | 7 |
| `relevance.py` | 8 | 8 |
| `search.py` | 6 | 6 |
| **Total** | **66** | **66** |

`source fingerprint unchanged: cafd616ae57f`. `C7` is the timeout case, counted as caught under
the convention above. One test is reported **skipped** in every run: the driver's own
isolation self-check detects that it is already inside a mutation run and declines to create a
nested worktree.

---

## `core/search.py` — the work budget (v2.9 A3, 2026-10-10)

Four mutants were added for the budget logic itself. The fix for a hang is exactly the kind of
code that attracts a plausible-looking regression, so it is mutation-covered like everything else.

| ID | Injected defect | Caught by |
|---|---|---|
| S9 | The work budget never runs out | non-termination ⇒ timeout, and the termination sweeps |
| S10 | `best_next_step` funds each probe from a fresh budget — **the original defect** | `test_best_next_step_spends_one_allowance_not_one_per_candidate` |
| S11 | `productive` funds each of its two searches separately | `test_productive_shares_its_allowance_across_both_searches` |
| S12 | A generation is charged *after* the `visited` test, so revisits are free | `test_the_budget_charges_every_generation_including_revisits` |

**S10 and S11 drove a test rewrite.** The first versions of both tests asserted only that the
budget was not overdrawn — and a per-probe budget leaves the caller's counter almost untouched,
which looks *thrifty*. Both mutants would have survived. The tests now grant exactly the opening
search's cost plus one unit: sharing the allowance makes every probe unaffordable (`None`), while
funding probes separately lets them succeed. The failure is decisive in either direction, and no
wall clock is involved.
