# Differential testing

Two independent methods must agree. The system decides *"does this conclusion follow"* by truth
table and *"can it be proved"* by resolution. The design leans on those agreeing: the proof
search is short-circuited whenever the truth table says there is nothing to find
(`docs/HLD.md` §6.6). Testing each against its own expectations would never catch a
misunderstanding they share — testing them against **each other** does.

Facts only: seeds, counts, and the command that regenerates them.

## Regenerate

```
python -m pytest backend/tests/test_differential.py -q -s
```

## Independence

The resolution side of Differential 1 is a **resolution closure written inside the test**, not
`search.distance`. Two reasons:

1. `search.distance` answers a harder question — how many steps a *student* needs — by exploring
   clause **sets**. On random knowledge bases it does not terminate in reasonable time. The first
   attempt at this test hung and had to be abandoned.
2. Refutation *existence* only needs the closure over derivable **clauses**, bounded by
   `3**symbols`, which finishes instantly — and sharing no code path with the truth table beyond
   the resolution rule itself is exactly what makes the comparison worth running.

## Results, 2026-10-10 (v2.9 A4)

| Test | Seed | Generator | Result |
|---|---|---|---|
| **D1** truth table vs resolution | `20261009` | ≤5 symbols, ≤6 clauses, random goal literal | **200 compared · 26 entailed · 174 not entailed**, plus **16 inconsistent — now checked, not skipped** |
| **D2** relevance safety (drops) | `20261010` | two disjoint symbol pools (`ABC`, `XYZ`) so a distractor component usually exists | **200 compared · 200 had clauses dropped** |
| **D3** relevance safety (keeps) | `20261011` | **fully-connected shuffled chains**, lengths 2–7 | **180 compared · 0 dropped, as required** |
| **D1-sweep** three further seeds | `20261109–11` | ≤4 symbols, ≤5 clauses, 120 cases each | **360 compared** |

**Agreement rate: 940 / 940 = 100%.** No disagreement has been observed.

## The two gaps closed in v2.9

**D1 used to `continue` past an inconsistent knowledge base.** That silently exempted the branch
the whole pipeline leans on hardest: `INCONSISTENT_PREMISES` is what stops the relevance filter and
the search from running at all (`docs/HLD.md` §6.5, §7). The entailment comparison genuinely does
not apply there — a contradiction entails everything — but a **stronger** claim does, and it is now
asserted in both directions on every case:

> the truth table finds **no model for the premises** ⟺ resolution derives the empty clause from
> **the premises alone**, with the goal excluded.

That is checked on the 16 inconsistent cases *and* as a negative on all 200 consistent ones, and
D1 now fails if fewer than 10 inconsistent cases occur — an unevidenced branch is not a passing
branch.

**D2 only ever measured the filter's willingness to DROP.** Its generator used two disjoint symbol
pools, so a distractor component almost always existed and "keep everything" was never required of
it. D3 adds knowledge bases where **every clause is reachable**, so a correct filter must keep all
of them: clause 0 shares the conclusion's symbol and clause *i* shares one with clause *i−1*. The
clauses are returned **shuffled**, and that is the point — in chain order a single-pass filter would
sweep the whole chain up by accident, so the shuffle is what makes transitivity load-bearing.

The failure D3 guards against is the worst one the system can produce: the verdict is decided
separately by truth table, so dropping a reachable clause would tell a student the conclusion
follows while leaving a board that can no longer prove it.

## Non-vacuity

Every test asserts its own evidence is not trivial — without this a generator that silently
produced one degenerate shape would still pass:

| Test | Guard |
|---|---|
| D1 | ≥10 entailed, ≥10 not entailed, ≥10 inconsistent |
| D2 | ≥20 cases where something was actually dropped; kept ⊆ input; verdict unchanged after filtering |
| D3 | ≥150 connected cases survived the inconsistency filter; `kept` equals the input exactly |
