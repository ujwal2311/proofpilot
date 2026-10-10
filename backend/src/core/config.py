"""Every numeric limit and seed in one place (docs/HLD.md section 8).

Constants live here so that no threshold is ever retyped in the API, the CLI or a script. Each
one records where its value came from -- a measurement, a design decision, or an assumption --
because a bare number is impossible to defend later.
"""

# Work budget for ONE search operation in core.search, counted in generated successor states.
#
# It replaced a per-BFS cap of 8,000 EXPANDED nodes at the Phase 5 gate (HLD v2.9 A3). That cap
# bound the wrong quantity twice over: one expansion emits hundreds of successors, none of which
# were counted, and best_next_step opened a fresh full-budget search per candidate step. Measured
# on the same machine as below: at the nominal 8,000 nodes a single search generated up to
# 184,058 states and held a 46,491-state frontier (~2.0 s), and one best_next_step call inside
# the documented input limits took 12.7 s. Generations are now charged one by one, and one
# allowance is shared by the whole operation, so the measured worst case is the budget.
#
# MEASURED on 2026-10-10 (Intel64 Family 6 Model 154, Windows 11, CPython 3.12.10) -- see
# docs/experiments/search_latency.md for the p50/p95/max table and the command that regenerates
# it. The value is set from that run, not guessed.
MAX_SEARCH_WORK = 60_000

# Input limits (docs/HLD.md section 3.4). DESIGN DECISIONS, not measurements: they keep a
# paragraph small enough that the truth table stays under 2**10 rows and that a student can hold
# the whole argument in view. Exceeding one is an error with a name, never a silent truncation.
MAX_SENTENCE_WORDS = 30
MAX_SENTENCES = 12

# Distinct facts allowed across a paragraph and its conclusion. DESIGN DECISION: it caps the
# truth table at 2**10 = 1024 rows (HLD section 6.4) and keeps the Facts screen readable.
MAX_FACTS = 10
