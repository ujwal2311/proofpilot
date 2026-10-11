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

# Entries kept in core.search's memoised-distance table. A bound is required because the API
# server is long-running: an unbounded cache is a memory leak, not an optimisation.
#
# MEASURED on 2026-10-11 (same machine), over 200 distinct own-question requests with the cache
# never cleared:
#   - one worst-case request confirms only 2 distances, because budget hits are never cached
#   - the table still grew to 1,062 entries, ~5.3 per request, linearly and without limit
#   - retained size was 1,666 bytes per entry, so 1,024 entries is a ~1.6 MiB ceiling
#
# 1,024 is therefore ~512x the worst single request -- every within-request hit still lands, which
# is where the whole benefit is -- while capping the table at a size a server can hold forever.
MAX_DISTANCE_CACHE = 1_024

# Input limits (docs/HLD.md section 3.4). DESIGN DECISIONS, not measurements: they keep a
# paragraph small enough that the truth table stays under 2**10 rows and that a student can hold
# the whole argument in view. Exceeding one is an error with a name, never a silent truncation.
MAX_SENTENCE_WORDS = 30
MAX_SENTENCES = 12

# Distinct facts allowed across a paragraph and its conclusion. DESIGN DECISION: it caps the
# truth table at 2**10 = 1024 rows (HLD section 6.4) and keeps the Facts screen readable.
MAX_FACTS = 10

# Bayesian Knowledge Tracing parameters (HLD sections 6.8, 17.7).
#
# These four are ASSUMED, not fitted. Fitting them would need response data from real students
# across many sessions, which this project does not have and will not invent -- the pilot is ten
# classmates, not a dataset. They are the conventional textbook starting values, and the numbers
# the design review worked the update through by hand (0.7098 correct, 0.1932 wrong), so they are
# also the figures the report can be checked against.
#
# The report must describe them as assumed. Presenting a chosen parameter as a measured one would
# be a false claim about the method, not a rounding difference.
BKT_P0 = 0.3  # prior probability the skill is already mastered
BKT_GUESS = 0.2  # answering correctly without the skill
BKT_SLIP = 0.1  # answering wrongly despite having it
BKT_TRANSIT = 0.15  # chance of learning the skill from one opportunity

# How far mastery is kept from 0 and 1. A clamp is REQUIRED: the BKT model never reaches either
# value, but float64 does. MEASURED on 2026-10-11, 23 consecutive correct answers drive P to
# EXACTLY 1.0, after which `posterior(1.0, wrong)` is 1.0 * s / (1.0 * s + 0) = 1.0, the skill can
# never move again, and the tutor keeps asserting mastery against evidence that contradicts it.
#
# The SIZE of the clamp is a DESIGN DECISION, derived from a stated teaching rule rather than from
# float64's resolution (sprint F1). The first version used 1e-9 -- enough headroom to be
# reversible, but the recovery length it implied, about ten consecutive wrong answers, was a side
# effect nobody had chosen. The rule now fixes it:
#
#   one or two wrong answers from a mastered student are SLIPS and must not revoke mastery;
#   a third consecutive wrong answer is evidence and must.
#
# The ceiling 1 - s is the state a long correct run settles on, so the rule is a condition on s.
# Bisecting the exact update with g=0.2, s=0.1, T=0.15 against a 0.95 threshold:
#   above ~1.1492e-3 the SECOND wrong answer already un-masters -- one slip too few
#   below ~1.6919e-4 the THIRD wrong answer still leaves the skill mastered -- never reversible
# 1e-3 is the only power of ten inside (1.6919e-4, 1.1492e-3], giving the trace 0.993247,
# 0.956154, 0.771866: two slips with margin, then a clear fall. 1 - 1e-3 still displays as 100%,
# so the guard is invisible to a student. Only the upper bound is reachable -- the transit term
# floors mastery at ~0.1714 -- but both are clamped so the invariant holds without a case split.
# `test_the_slack_is_inside_the_window_the_rule_allows` re-derives the window from the shipped
# formulas, so changing g, s, T or the threshold fails the build instead of silently moving this.
MASTERY_SLACK = 1e-3

# Mastery required in EVERY active skill before the exercise set is finished (HLD section 9).
# DESIGN DECISION, deliberately high: at 0.95 a student cannot finish on a lucky streak, and the
# BKT update reaches it in about eight consecutive correct answers per skill.
MASTERY_THRESHOLD = 0.95

# Seed for every generator in the tests and the experiment scripts (rule 4: seed every random
# generator from here). One value, so a failing property case is reproducible by anyone who runs
# the suite -- an unseeded generator can expose a bug but cannot reproduce it.
RANDOM_SEED = 20261012

# Board limits a REQUEST is held to (HLD section 8's tamper list). DESIGN DECISIONS, and they
# bound a hostile or corrupt payload rather than a student's honest work: the relevance bound
# keeps a bank exercise at 7 clauses, so 20 is generous for a long own question while still
# refusing a body built to make the server do unbounded work.
MAX_BOARD_CLAUSES = 20
MAX_CLAUSE_LITERALS = 6
