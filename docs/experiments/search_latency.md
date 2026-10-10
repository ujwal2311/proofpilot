# Search termination and latency

`core.search` explores clause **sets**, so its cost grows exponentially in the length of the
proof. That is a product risk, not a test-design detail: a hint that never arrives is a broken
feature. This file records what the search actually costs, what bounds it, and where it gives up.

Facts only: the machine, the command that regenerates each number, and the measurement.

## Regenerate

```powershell
python -m pytest backend/tests/test_search_budget.py -q -s          # the always-on checks
$env:PROOFPILOT_SLOW = "1"; python -m pytest backend/tests/test_search_budget.py -q -s
```

The second form adds the 400-case production-budget sweep (~55 s), which is skipped by default
because the suite runs six times per CI push.

**Machine:** Intel64 Family 6 Model 154, Windows 11, CPython 3.12.10.
**Date:** 2026-10-10. **Commit:** `f651d3b`. **Budget:** `MAX_SEARCH_WORK = 60,000`.

## The defect this replaced

The previous bound was `MAX_SEARCH_NODES = 8,000`, counted in **expanded nodes**. It bounded the
wrong quantity, twice over:

| | Measured at the nominal 8,000-node cap |
|---|---|
| Expansions charged | 8,000 |
| Successor states actually **generated** | up to **184,058** — 23× the cap, none of them charged |
| Peak frontier held in memory | **46,491** states |
| One `distance` call | up to **2.4 s** |
| One `best_next_step` call | **12.7 s** — it opened a fresh full-budget search per candidate step, and a budget hit is deliberately never cached, so every probe paid the whole allowance again |

Both inputs were inside the documented limits (≤10 facts, ≤20 clauses). The fix charges every
generated state one unit, and gives **one allowance to one public call** rather than one per
search.

## Cost by proof depth — why the budget is what it is

`best_next_step` on a chain (`A`, `A→B`, …, `¬Z`) plus one distractor pair. A chain is the worst
realistic shape: every clause is load-bearing, so nothing can be filtered and no shortcut exists.

| Proof length | Clauses | Work units | Wall time | Hint |
|---|---|---|---|---|
| 3 | 6 | 28 | 0.3 ms | yes |
| 4 | 7 | 167 | 1.6 ms | yes |
| **5** | **8** | **1,051** | **12.7 ms** | yes ← deepest proof in the bank (§9 bands) |
| 6 | 9 | 6,921 | 88 ms | yes |
| 7 | 10 | 47,305 | 691 ms | yes ← deepest the budget answers |
| 8 | 11 | 60,000 (exhausted) | 835 ms | **no — rule-based fallback** |

Work grows ≈ **7× per proof step**. No budget buys depth; a budget only decides where the
fallback starts.

**Why 60,000.** It is ~57× the worst case the exercise bank can present (1,051 units for a 5-step
proof), it covers own-question proofs up to depth 7, and it keeps the worst observed wall time
near 1 s. Doubling it to 120,000 bought one third of a proof step and pushed the worst case to
3.8 s; halving it to 30,000 began to bite the provable tail of the random sweep (worst 15,168).

## Latency

`best_next_step` at the production budget. The worst-case rows are deterministic in work spent,
so their spread is machine noise rather than input variation.

| Workload | p50 | p95 | max |
|---|---|---|---|
| Bank worst case (8 clauses, 5-step proof), 15 runs | **11.0 ms** | 11.7 ms | **11.7 ms** |
| Own-question worst case (10 clauses, 7-step proof), 5 runs | **582.8 ms** | 585.4 ms | **586.3 ms** |
| Random sweep, bank shape (≤7 clauses, ≤6 facts), 200 cases | 0.10 ms | 624.87 ms | 1,766.28 ms |
| Random sweep, own shape (≤20 clauses, ≤10 facts), 200 cases | 2.18 ms | 816.28 ms | 1,573.46 ms |

The random sweeps are **slower than the product** and deliberately so. They are dominated by
clause sets with **no refutation at all** (165 of 200 at bank shape), which exhaust the budget
before giving up — and V-2 (HLD §6.6) means the product never searches those: entailment is
settled by truth table first. They are measured anyway because robustness must not depend on the
caller being correct.

## Targets, stated as goals

These are **goals**, not guarantees, and they are not claims about any machine but the one above.
A shared CI runner under unknown load is not a benchmark, so the automated assertion is a
deliberately loose 10 s ceiling whose job is to catch a regression of orders of magnitude — which
is exactly what the defect above was.

| Goal | Status against the measurement |
|---|---|
| A hint within **1 s** for any bank exercise | met with ~85× margin (11.7 ms worst) |
| A hint or an explicit fallback within **1 s** for an own question | met for proofs to depth 7 (586 ms); depth 8+ falls back at 835 ms |
| Every input inside the documented limits **terminates** | 500 seeded random states per run, each returning a count, `None`, or `GoalUnreachableError` |
