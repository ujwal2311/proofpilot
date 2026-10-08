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

## Results, 2026-10-09

| Test | Seed | Generator | Result |
|---|---|---|---|
| **D1** truth table vs resolution | `20261009` | ≤5 symbols, ≤6 clauses, random goal literal | **200 compared · 26 entailed · 174 not entailed · 16 skipped** (inconsistent premises, where the guarantee does not apply) |
| **D2** relevance safety | `20261010` | two disjoint symbol pools (`ABC`, `XYZ`) so a distractor component usually exists | **200 compared · 200 had clauses dropped** |
| **D1-sweep** three further seeds | `20261109–11` | ≤4 symbols, ≤5 clauses, 120 cases each | **360 compared** |

**Agreement rate: 760 / 760 = 100%.** No disagreement has been observed.

D2 additionally asserts, on every case, that the kept clauses are a subset of the input and that
the verdict on the filtered set equals the verdict on the full set.

Both tests assert their own evidence is not vacuous: D1 requires at least 10 of each verdict, and
D2 requires at least 20 cases where something was actually dropped. Without those a generator
that silently produced one trivial shape would still pass.
