# Mutation testing log

Test-quality evidence. A passing suite proves nothing on its own, so after each module the
implementation is deliberately broken and the suite re-run. A mutation that survives means the
tests cannot see that defect.

Facts only: every row is an injected change and the observed pytest result. No claim is made
beyond the counts.

Method: inject one defect, run `python -m pytest`, record the result, revert, verify the tree is
clean. Machine: Intel64 / Windows 11 / CPython 3.12.10.

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
