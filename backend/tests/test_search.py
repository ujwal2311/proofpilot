"""Tests for core.search -- BFS distance, productivity and hints (docs/HLD.md section 6.6).

Written before the implementation. Fixtures are clause sets built inline: core reads no files
(HLD v2.4), and at this phase neither english.py nor cnf.py exists to produce them.
"""

import pytest
from src.core.logic import Clause, canonical
from src.core.search import (
    GoalUnreachableError,
    best_next_step,
    candidate_steps,
    clear_distance_cache,
    distance,
    fallback_step,
    productive,
    successors,
)

CAP = 50_000  # far above anything these fixtures need; cap behaviour is tested explicitly


def C(*literals: str) -> Clause:
    return frozenset(literals)


def S(*clauses: Clause) -> frozenset[Clause]:
    return frozenset(clauses)


# The rain example, carried from the original brief:
#   "if it rains then we get wet" -> {~R, W};  "it rains" -> {R};  negated goal "we get wet" -> {~W}
# Shortest proof is 2: {R}+{~R,W} -> {W}, then {W}+{~W} -> [].
RAIN = S(C("~R", "W"), C("R"), C("~W"))

# A three-step chain: A, A->B, B->C, negated goal ~C.
CHAIN3 = S(C("~A", "B"), C("~B", "C"), C("A"), C("~C"))

# The same chain plus a self-contained distractor pair. Resolving D with ~D,E is a perfectly
# VALID step that gets the student no closer -- the only way to observe "valid but unproductive".
CHAIN3_WITH_DISTRACTOR = CHAIN3 | S(C("D"), C("~D", "E"))

# No refutation exists: nothing ever clashes with ~C. BFS exhausts rather than hitting the cap.
UNREACHABLE = S(C("~A", "B"), C("A"), C("~C"))

# A chain whose symbols sort AFTER a self-contained distractor, so the canonically first legal
# step ({A}+{~A,B} -> {B}) is a dead end. Any "just take the first legal move" implementation
# picks wrong here, which is exactly what makes this fixture worth having.
DISTRACTOR_FIRST = S(C("A"), C("~A", "B"), C("P"), C("~P", "Q"), C("~Q", "R"), C("~R"))

# The canonically first pair ({A,B}+{~A,C}) clashes, but neither clause is a unit; the unit
# clause {Z} sorts last. Distinguishes "shortest clause first" from "canonical order first".
UNIT_SORTS_LAST = S(C("A", "B"), C("~A", "C"), C("Z"), C("~Z", "Y"))


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    # The distance cache is module-level state. Clearing it per test keeps every test
    # independent and makes a stale-cache bug visible rather than order-dependent.
    clear_distance_cache()


# ----------------------------------------------------------------------------------- successors


def test_successors_add_exactly_one_new_clause() -> None:
    for child in successors(RAIN):
        assert len(child) == len(RAIN) + 1
        assert RAIN < child


def test_successors_skip_tautologies_and_clauses_already_present() -> None:
    # {P,Q} and {~P,~Q} resolve only to tautologies, so the state has no legal successor at all.
    assert successors(S(C("P", "Q"), C("~P", "~Q"))) == []


def test_a_clause_pair_offers_at_most_one_legal_step() -> None:
    # Follows from the two-pivot theorem (HLD 6.7): one pivot gives exactly one resolvent, and
    # two or more pivots make every resolvent a tautology, which is filtered out. Pinned here
    # because it is why sorting the resolvents of a single pair can never change the order --
    # the sort stays as a local determinism guard rather than a load-bearing step.
    for state in (RAIN, CHAIN3, CHAIN3_WITH_DISTRACTOR, DISTRACTOR_FIRST, UNIT_SORTS_LAST):
        pairs = [(a, b) for a, b, _ in candidate_steps(state)]
        assert len(pairs) == len(set(pairs))


def test_successors_are_canonically_ordered() -> None:
    # Determinism (HLD 17.10): the same state must expand in the same order in every process,
    # or hints would differ between runs.
    #
    # Rebuilding the frozenset in a different order would NOT test this: equal frozensets
    # iterate identically within a process, so any implementation would pass. The real
    # assertion is that the emitted order IS canonically sorted.
    keys = [(canonical(a), canonical(b), canonical(r)) for a, b, r in candidate_steps(CHAIN3)]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys)), "a step must not be offered twice"

    # successors() must follow the same order, since it is derived from candidate_steps().
    added = [next(iter(child - CHAIN3)) for child in successors(CHAIN3)]
    assert [canonical(c) for c in added] == [k[2] for k in keys]


# -------------------------------------------------------------------------------------- distance


def test_bfs_distance_fixture() -> None:
    assert distance(RAIN, CAP) == 2
    assert distance(CHAIN3, CAP) == 3
    assert distance(CHAIN3_WITH_DISTRACTOR, CAP) == 3


def test_distance_is_zero_when_the_empty_clause_is_already_present() -> None:
    assert distance(RAIN | S(C()), CAP) == 0


def test_search_cap_returns_none_not_hang() -> None:
    assert distance(RAIN, 1) is None


def test_search_raises_when_goal_is_unreachable() -> None:
    # Exhaustion is NOT a cap hit. Returning None for both would tell the caller "too hard"
    # when the truth is "impossible", so this raises instead. The HLD's short-circuit means a
    # correct caller never reaches it; this is the guard that proves the caller was wrong.
    with pytest.raises(GoalUnreachableError):
        distance(UNREACHABLE, CAP)


def test_distance_cache_returns_the_same_answer_and_never_caches_a_cap_hit() -> None:
    assert distance(RAIN, CAP) == 2
    assert distance(RAIN, CAP) == 2
    clear_distance_cache()
    # A cap hit must not be stored: it depends on max_nodes, so caching it under the state
    # alone would poison a later call with a larger budget.
    assert distance(RAIN, 1) is None
    assert distance(RAIN, CAP) == 2


# ------------------------------------------------------------------------------------ productive


def test_productive_iff_distance_drops_by_one() -> None:
    before = CHAIN3_WITH_DISTRACTOR
    resolvent = C("B")  # from {A} + {~A,B}, the first step of a shortest proof
    assert resolvent not in before
    assert productive(before, before | S(resolvent), CAP) is True

    # Valid, but no closer: the distractor pair resolves to {E}, which no proof needs.
    assert productive(before, before | S(C("E")), CAP) is False


def test_every_valid_step_changes_distance_by_zero_or_minus_one() -> None:
    # The invariant the whole productivity notion rests on (HLD 6.6). A step must never make
    # the proof longer -- adding a clause can only ever help.
    for state in (RAIN, CHAIN3, CHAIN3_WITH_DISTRACTOR):
        before = distance(state, CAP)
        for child in successors(state):
            assert distance(child, CAP) in (before, before - 1)


def test_productive_is_none_when_either_search_hits_the_cap() -> None:
    assert productive(RAIN, RAIN | S(C("W")), 1) is None


# --------------------------------------------------------------------------------- best_next_step


def test_best_next_step_starts_a_shortest_proof() -> None:
    step = best_next_step(RAIN, CAP)
    assert step is not None
    a, b, resolvent = step
    assert {a, b} <= RAIN
    assert resolvent in {C("W"), C("~R")}  # either unit resolvent begins a 2-step proof
    assert productive(RAIN, RAIN | S(resolvent), CAP) is True


def test_best_next_step_skips_a_legal_but_useless_first_candidate() -> None:
    # The canonically first legal step on this fixture is the distractor {A}+{~A,B} -> {B},
    # which is valid and gets the student nowhere. Suggesting it would be worse than useless:
    # the hint is supposed to be the start of a SHORTEST proof, not the first thing that fits.
    assert candidate_steps(DISTRACTOR_FIRST)[0][2] == C("B")
    step = best_next_step(DISTRACTOR_FIRST, CAP)
    assert step is not None
    assert step[2] != C("B")
    assert productive(DISTRACTOR_FIRST, DISTRACTOR_FIRST | S(step[2]), CAP) is True


def test_best_next_step_is_deterministic() -> None:
    first = best_next_step(CHAIN3, CAP)
    clear_distance_cache()
    assert best_next_step(frozenset(reversed(list(CHAIN3))), CAP) == first


def test_best_next_step_is_none_when_already_solved() -> None:
    assert best_next_step(RAIN | S(C()), CAP) is None


# ---------------------------------------------------------------------------------- fallback_step


def test_cap_returns_fallback_hint() -> None:
    # When the search budget is exhausted the student still gets a legal move, chosen by a cheap
    # rule rather than by search. It is a suggestion, not a shortest step.
    assert distance(CHAIN3, 1) is None
    step = fallback_step(CHAIN3)
    assert step is not None
    a, b, resolvent = step
    assert {a, b} <= CHAIN3
    assert resolvent not in CHAIN3


def test_fallback_prefers_the_shortest_clause() -> None:
    # "Prefer resolving with the shortest clause" -- unit clauses drive a refutation forward.
    # On this fixture the canonically FIRST clashing pair has no unit clause in it, while a unit
    # clause sorts last, so an implementation that ignores length picks the two-literal pair.
    assert candidate_steps(UNIT_SORTS_LAST)[0] == (C("A", "B"), C("~A", "C"), C("B", "C"))
    a, b, _ = fallback_step(UNIT_SORTS_LAST)
    assert min(len(a), len(b)) == 1, "a unit clause was available and should have been chosen"


def test_fallback_is_deterministic() -> None:
    # Order within the state cannot matter, and the choice must be reproducible across runs.
    assert fallback_step(CHAIN3) == fallback_step(frozenset(reversed(list(CHAIN3))))
    assert fallback_step(UNIT_SORTS_LAST) == fallback_step(frozenset(UNIT_SORTS_LAST))


def test_fallback_is_none_when_no_legal_step_exists() -> None:
    assert fallback_step(S(C("P", "Q"), C("~P", "~Q"))) is None
