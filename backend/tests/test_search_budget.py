"""Termination and latency of core.search (docs/HLD.md v2.9 A3, §6.6).

CONTRACT, and why each part is asserted here rather than reasoned about:

  1. TERMINATION is a product property, not a test-design detail. Every state inside the
     documented input limits must leave `distance`, `productive` and `best_next_step` with an
     `int` or `None` -- or `GoalUnreachableError`, which is also an answer -- never a hang.
  2. The bound is DETERMINISTIC. Work is counted in generated successor states, so the same
     input consumes the same budget on every machine. A wall-clock cut-off would make a hint
     depend on load, and a non-reproducible hint cannot be tested at all.
  3. One public call draws on ONE allowance. The original defect was not a slow search: it was
     `best_next_step` opening a fresh full-budget search per candidate step, and a budget hit
     being deliberately uncached, so each probe paid the whole allowance again. Pinned below.
  4. Latency is a GOAL, measured and reported, not a guarantee. The assertion is a generous CI
     bound; the real numbers live in docs/experiments/search_latency.md.
"""

import os
import random
import statistics
import time

import pytest
from src.core.config import MAX_SEARCH_WORK
from src.core.search import (
    GoalUnreachableError,
    Work,
    best_next_step,
    candidate_steps,
    clear_distance_cache,
    distance,
    fallback_step,
    productive,
)

SEED = 20261010
PROPERTY_BUDGET = 2_000  # small on purpose: the property is budget-independent, so keep CI fast
CI_LATENCY_BOUND_S = 10.0  # ~6x the measured worst case; a shared CI runner is not a benchmark
SLOW = "PROOFPILOT_SLOW"


def _random_state(rng: random.Random, symbols: str, max_clauses: int) -> frozenset:
    """A clause set inside the product's input limits (HLD §3.4: MAX_FACTS, MAX_SENTENCES)."""

    def clause() -> frozenset:
        chosen = rng.sample(symbols, rng.randint(1, min(3, len(symbols))))
        return frozenset(("" if rng.random() < 0.5 else "~") + s for s in chosen)

    kb = [clause() for _ in range(rng.randint(1, max_clauses))]
    goal = frozenset({("~" if rng.random() < 0.5 else "") + rng.choice(symbols)})
    return frozenset([*kb, goal])


# Bank exercises are bounded at <=7 relevant clauses over <=6 facts (HLD §6.6); own questions by
# MAX_FACTS=10 and the 20-clause API limit (HLD §8). Both shapes are swept.
SHAPES = {"bank": ("ABCDEF", 7), "own": ("ABCDEFGHIJ", 20)}


def _chain(length: int) -> frozenset:
    """`A`, `A->B`, ... plus the negated goal: the deepest proof a bank exercise may need.

    A chain is the worst realistic bank shape because every clause is load-bearing -- there is no
    distractor the relevance filter could remove and no shortcut the search could take.
    """
    letters = "ABCDEFGHIJ"[: length + 1]
    clauses = [frozenset({letters[0]}), frozenset({"~" + letters[length]})]
    clauses += [frozenset({"~" + letters[i], letters[i + 1]}) for i in range(length)]
    return frozenset(clauses)


DISTRACTOR = {frozenset({"Y"}), frozenset({"~Y", "Z"})}

# MEASURED 2026-10-10 (docs/experiments/search_latency.md): work grows ~7x per proof step --
# 28, 167, 1051, 6921, 47305 units for proofs of 3, 4, 5, 6, 7. That is BFS over clause SETS and
# no budget can buy depth, so the budget is chosen to cover the deepest proof the bank contains
# (5, §9 bands) with ~57x headroom, and own questions degrade at depth 8.
WORST_BANK = _chain(4) | DISTRACTOR  # 8 clauses, 5-step proof: the deepest a bank exercise gets
WORST_OWN = _chain(6) | DISTRACTOR  # 10 clauses, 7-step proof: the deepest the budget answers
BEYOND_BUDGET = _chain(7) | DISTRACTOR  # 11 clauses, 8-step proof: the first that falls back


# --------------------------------------------------------------------------------- termination


@pytest.mark.parametrize("shape", sorted(SHAPES), ids=sorted(SHAPES))
def test_every_random_state_terminates_within_its_budget(shape: str, record_property) -> None:
    rng = random.Random(SEED)
    symbols, max_clauses = SHAPES[shape]
    answered = exhausted = unreachable = 0

    for case in range(250):
        state = _random_state(rng, symbols, max_clauses)
        clear_distance_cache()
        work = Work(PROPERTY_BUDGET)
        try:
            result = best_next_step(state, work)
        except GoalUnreachableError:
            unreachable += 1
            continue
        assert result is None or len(result) == 3, f"case {case}: {result!r}"
        answered += result is not None
        exhausted += result is None
        # The whole point of a deterministic budget: work spent is exactly what was granted
        # minus what is left, and it can never be overdrawn.
        assert 0 <= work.left <= PROPERTY_BUDGET, f"case {case}: budget overdrawn"

    assert answered + exhausted + unreachable == 250
    assert answered >= 10, "almost nothing was provable -- the sweep proves little"
    tally = f"{answered} answered, {exhausted} out of budget, {unreachable} unreachable"
    record_property(shape, tally)
    print(f"\n{shape}: {tally}")


def test_distance_and_productive_also_terminate_on_random_states() -> None:
    # best_next_step is the expensive entry point, but the other two are called from the API on
    # their own (HLD §17.8), so neither may be left to the one sweep above.
    rng = random.Random(SEED + 1)
    for _ in range(250):
        state = _random_state(rng, "ABCDEFGHIJ", 20)
        clear_distance_cache()
        try:
            # Called once and bound: a budget hit is deliberately never cached, so asserting on
            # two separate calls would pay for the whole search twice.
            answer = distance(state, PROPERTY_BUDGET)
            assert answer is None or isinstance(answer, int), "a count or an explicit None"
            steps = candidate_steps(state)
            if steps:
                verdict = productive(state, state | {steps[0][2]}, PROPERTY_BUDGET)
                assert verdict in (True, False, None)
        except GoalUnreachableError:
            continue


# ---------------------------------------------------------- one call, one allowance (the defect)


def _opening_cost(state: frozenset) -> int:
    """What the first `distance` call on `state` costs, so a test can grant exactly that much."""
    clear_distance_cache()
    work = Work(MAX_SEARCH_WORK)
    distance(state, work)
    return MAX_SEARCH_WORK - work.left


def test_best_next_step_spends_one_allowance_not_one_per_candidate() -> None:
    # THE regression test for the hang. Before the fix every candidate probe opened a fresh
    # full-budget search, so one hint cost |candidates| x the worst single search -- measured at
    # 12.7 s inside the documented input limits.
    #
    # Asserting "the budget was not overdrawn" would NOT catch that: a per-probe budget leaves
    # the caller's counter almost untouched, which looks thrifty. So the budget granted here is
    # exactly enough for the opening search and one unit more. Sharing it => every probe is
    # unaffordable => None. Not sharing it => each probe gets a full allowance and succeeds.
    assert len(candidate_steps(WORST_BANK)) >= 5, "fixture must offer several probes"
    tight = Work(_opening_cost(WORST_BANK) + 1)
    clear_distance_cache()
    assert best_next_step(WORST_BANK, tight) is None, "a probe was funded from outside the budget"
    assert tight.left == 0, "the shared allowance should be spent, not bypassed"


def test_productive_shares_its_allowance_across_both_searches() -> None:
    # Same reasoning: fund the first search and nothing else. The second must then be
    # unaffordable, which makes productivity undecidable -- reported as None, never guessed.
    step = candidate_steps(WORST_BANK)[0]
    after = WORST_BANK | {step[2]}
    tight = Work(_opening_cost(WORST_BANK) + 1)
    clear_distance_cache()
    assert productive(WORST_BANK, after, tight) is None
    assert tight.left == 0, "the shared allowance should be spent, not bypassed"


def test_the_budget_charges_every_generation_including_revisits() -> None:
    # A child is charged BEFORE the `visited` test, because generating it is what costs -- the
    # resolvent was computed whether or not the state turns out to be new. Charging only new
    # states would let a search with heavy revisiting run far past its allowance, which is the
    # same class of defect as counting expansions instead of generations.
    #
    # MEASURED 2026-10-10 and verified identical under PYTHONHASHSEED 0, 4242 and 99: successor
    # order is canonical, so this count is deterministic rather than hash-dependent.
    assert _opening_cost(WORST_BANK) == 798


def test_a_bank_exercise_is_answered_far_inside_the_production_budget() -> None:
    # The budget must be generous for every state the product will actually search, not merely
    # survivable. V-2 means search runs only on ENTAILED states, and the worst of those is a
    # chain. MEASURED 2026-10-10: 1,051 units for the 5-step bank worst case, so the production
    # budget carries ~57x headroom over anything the bank can ask for.
    for state, limit in ((WORST_BANK, 5_000), (WORST_OWN, MAX_SEARCH_WORK)):
        clear_distance_cache()
        work = Work(MAX_SEARCH_WORK)
        assert best_next_step(state, work) is not None, "a provable state must yield a hint"
        assert MAX_SEARCH_WORK - work.left <= limit


def test_a_proof_deeper_than_the_budget_degrades_instead_of_hanging() -> None:
    # The honest limitation, asserted rather than hoped for (HLD §14). States are SETS of
    # clauses, so BFS cost grows ~7x per proof step and no budget buys depth. An own question
    # needing 8 steps therefore gets the rule-based fallback -- bounded, deterministic, and
    # labelled a suggestion (HLD §6.6 "Cap fallback") -- not a hang and not a guess.
    clear_distance_cache()
    work = Work(MAX_SEARCH_WORK)
    assert best_next_step(BEYOND_BUDGET, work) is None
    assert work.left == 0, "the budget should be spent, not abandoned early"
    assert fallback_step(BEYOND_BUDGET) is not None, "the student must still get a legal move"


# ------------------------------------------------------------------------------------- latency


def _latency_ms(state: frozenset, repeats: int) -> list[float]:
    samples = []
    for _ in range(repeats):
        clear_distance_cache()  # every sample pays full price; a warm cache would flatter us
        started = time.perf_counter()
        best_next_step(state, MAX_SEARCH_WORK)
        samples.append((time.perf_counter() - started) * 1000)
    return sorted(samples)


@pytest.mark.parametrize(
    ("label", "state", "repeats"),
    # Fewer repeats for the own-question case only because it costs ~0.6 s each and the work it
    # does is deterministic -- the spread is machine noise, not input variation.
    [("bank worst case", WORST_BANK, 15), ("own-question worst case", WORST_OWN, 5)],
)
def test_worst_case_latency_stays_inside_a_generous_bound(
    label: str, state: frozenset, repeats: int, record_property
) -> None:
    samples = _latency_ms(state, repeats)
    p50 = statistics.median(samples)
    p95 = samples[int(0.95 * (len(samples) - 1))]
    summary = f"p50={p50:.1f}ms p95={p95:.1f}ms max={samples[-1]:.1f}ms"
    record_property(label, summary)
    print(f"\nLATENCY {label}: {summary}")
    # A GOAL is stated in the HLD (a hint <=1 s for bank exercises); this bound is deliberately
    # much looser, because a shared CI runner under an unknown load is not a benchmark. It is
    # here to catch a regression of orders of magnitude, which is what the defect was.
    assert samples[-1] < CI_LATENCY_BOUND_S * 1000, f"{label}: {summary}"


@pytest.mark.skipif(
    os.environ.get(SLOW) != "1",
    reason=f"set {SLOW}=1 to run the full 400-case production-budget sweep (~60 s)",
)
def test_full_sweep_at_the_production_budget(record_property) -> None:
    # Regenerates the table in docs/experiments/search_latency.md. Skipped by default: at the
    # production budget this takes ~60 s, and the suite runs six times per CI push.
    for shape, (symbols, max_clauses) in sorted(SHAPES.items()):
        rng = random.Random(SEED)
        samples = []
        for _ in range(200):
            state = _random_state(rng, symbols, max_clauses)
            clear_distance_cache()
            started = time.perf_counter()
            try:
                best_next_step(state, MAX_SEARCH_WORK)
            except GoalUnreachableError:
                pass
            samples.append((time.perf_counter() - started) * 1000)
        samples.sort()
        summary = (
            f"p50={statistics.median(samples):.2f}ms "
            f"p95={samples[int(0.95 * (len(samples) - 1))]:.2f}ms max={samples[-1]:.2f}ms"
        )
        record_property(f"sweep-{shape}", summary)
        print(f"\nSWEEP {shape} (200 cases): {summary}")
        assert samples[-1] < CI_LATENCY_BOUND_S * 1000
