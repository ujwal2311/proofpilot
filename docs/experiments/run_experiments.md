# Evaluation: simulation, hint soundness, search cost

**Date:** 2026-10-12. **Commit:** `8b76db3`. **Python:** 3.12.10. **OS:** Windows-11-10.0.26300-SP0.

Regenerate: `python scripts/run_experiments.py --write`.

## Simulation (docs/results.png, docs/results_simulation.csv)

| policy | premature-release % | mean exercises | mean over-practice |
|---|---|---|---|
| baseline (fixed-N) | 21.0 | 8.0 | 4.5 |
| adaptive-matched | 2.6 | 7.6 | 2.7 |
| adaptive-mismatched | 4.8 | 11.5 | 3.8 |

## T2 — hint soundness (seeded random walks)

Every level-3 hint checked was valid and non-worsening (section 6.6). A failure would
raise during the run, not appear as a row here.

| exercise | walks | level-3 hints checked |
|---|---|---|
| ex-01 | 10 | 27 |
| ex-02 | 10 | 23 |
| ex-03 | 10 | 44 |
| ex-04 | 10 | 44 |
| ex-05 | 10 | 24 |
| ex-06 | 10 | 24 |
| ex-07 | 10 | 26 |
| ex-08 | 10 | 96 |
| ex-09 | 10 | 81 |
| ex-10 | 10 | 53 |

## T3 — search cost

| exercise | shortest proof | states generated | median time | budget hits |
|---|---|---|---|---|
| ex-01 | 2 | 3 | 0.02 ms | 0 |
| ex-02 | 2 | 3 | 0.02 ms | 0 |
| ex-03 | 3 | 19 | 0.10 ms | 0 |
| ex-04 | 3 | 19 | 0.12 ms | 0 |
| ex-05 | 2 | 4 | 0.03 ms | 0 |
| ex-06 | 2 | 3 | 0.03 ms | 0 |
| ex-07 | 2 | 3 | 0.02 ms | 0 |
| ex-08 | 4 | 182 | 2.03 ms | 0 |
| ex-09 | 4 | 158 | 1.89 ms | 0 |
| ex-10 | 3 | 28 | 0.28 ms | 0 |
| ex-11 | does not entail | — | — | — |
| ex-12 | does not entail | — | — | — |

Machine-dependent: times are not comparable across machines; see
docs/experiments/search_latency.md.
