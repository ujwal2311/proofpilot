"""Every numeric limit and seed in one place (docs/HLD.md section 8).

Constants live here so that no threshold is ever retyped in the API, the CLI or a script. Each
one records where its value came from -- a measurement, a design decision, or an assumption --
because a bare number is impossible to defend later.
"""

# Node budget for a single BFS in core.search.
#
# MEASURED at the Phase 3 gate on 2026-10-08 (Intel64 Family 6 Model 154, Windows 11,
# CPython 3.12.10), not guessed:
#   - worst legal bank state (7 clauses, 6 symbols, shortest proof 5) needed 184 nodes / 13.9 ms
#   - cost per expanded node was flat at ~64 microseconds across binding caps of 50-180
#   - 8,000 nodes is therefore ~43x the worst measured requirement and ~0.5 s worst case,
#     which keeps a hint feeling immediate
#
# Per-node cost rises with the number of clauses in the state, so a much larger own-question
# paragraph will be slower per node than the figure above. That is the intended behaviour: such
# a search hits the cap and degrades to search.fallback_step() rather than hanging.
MAX_SEARCH_NODES = 8_000
