"""Tests for core.relevance -- which clauses the conclusion can reach (HLD sections 6.5, 7).

Written before the implementation. The filter is only sound because consistency was checked
first (the §6.5 proof needs the dropped clauses to be independently satisfiable), so misusing it
must be impossible rather than merely discouraged.
"""

import pytest
from src.core.english import ErrorCode, ParseError
from src.core.entail import Entailment, Verdict, check
from src.core.relevance import filter_clauses


def C(*literals: str):
    return frozenset(literals)


CONSISTENT = Entailment(Verdict.ENTAILED)

# A -> B -> C, with a self-contained D -> E pair that the conclusion can never reach.
CHAIN = [C("~A", "B"), C("~B", "C"), C("A")]
DISTRACTOR = [C("D"), C("~D", "E")]
GOAL_C = [C("~C")]


def test_a_distractor_component_is_dropped() -> None:
    result = filter_clauses([*CHAIN, *DISTRACTOR], GOAL_C, CONSISTENT)
    assert set(result.kept) == set(CHAIN)
    assert set(result.dropped) == set(DISTRACTOR)


def test_a_chain_of_three_facts_is_kept_whole() -> None:
    # Reachability is transitive: C shares a fact with the B->C clause, which shares one with
    # A->B, which shares one with A. Stopping at the first hop would delete half the proof.
    result = filter_clauses(CHAIN, GOAL_C, CONSISTENT)
    assert set(result.kept) == set(CHAIN)
    assert result.dropped == ()


def test_nothing_is_dropped_when_everything_connects() -> None:
    assert filter_clauses([C("A", "B"), C("~B", "C")], [C("~C")], CONSISTENT).dropped == ()


def test_the_filter_refuses_an_inconsistent_verdict() -> None:
    # Misuse made impossible, not merely discouraged. With inconsistent premises the
    # contradiction can live entirely inside the dropped component, and filtering would destroy
    # the only refutation -- the exact failure the HLD's correctness argument rules out.
    with pytest.raises(ParseError) as caught:
        filter_clauses(CHAIN, GOAL_C, Entailment(Verdict.INCONSISTENT_PREMISES))
    assert caught.value.code is ErrorCode.RELEVANCE_REQUIRES_CONSISTENCY


def test_the_filter_accepts_a_not_entailed_verdict() -> None:
    # Only INCONSISTENT is refused: an argument that simply does not follow is still a
    # well-formed set of premises, and the student may still explore it.
    result = filter_clauses(CHAIN, [C("~Z")], Entailment(Verdict.NOT_ENTAILED, {"Z": False}))
    assert result.dropped == tuple(sorted(CHAIN, key=lambda c: tuple(sorted(c))))


def test_output_is_canonically_ordered() -> None:
    result = filter_clauses([*DISTRACTOR, *CHAIN], GOAL_C, CONSISTENT)
    for group in (result.kept, result.dropped):
        assert list(group) == sorted(group, key=lambda c: tuple(sorted(c)))


def test_kept_and_dropped_partition_the_input() -> None:
    everything = [*CHAIN, *DISTRACTOR]
    result = filter_clauses(everything, GOAL_C, CONSISTENT)
    assert set(result.kept) | set(result.dropped) == set(everything)
    assert not set(result.kept) & set(result.dropped)


def test_filtering_preserves_the_verdict() -> None:
    # The guarantee that makes the filter safe to apply at all: it may shrink the clause set,
    # but it must never change the answer.
    everything = [*CHAIN, *DISTRACTOR]
    before = check(everything, GOAL_C)
    kept = filter_clauses(everything, GOAL_C, before).kept
    assert check(list(kept), GOAL_C).verdict is before.verdict
