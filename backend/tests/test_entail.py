"""Tests for core.entail -- truth-table entailment (docs/HLD.md sections 6.4, 17.5).

Written before the implementation. Entailment is decided exhaustively rather than by search, so
that "is this argument valid" and "can the student find a proof" stay separate questions -- which
is what lets the search be short-circuited when the answer is already known.
"""

import time

import pytest
from src.core.english import ErrorCode, ParseError
from src.core.entail import Entailment, Verdict, check, symbols_of


def C(*literals: str):
    return frozenset(literals)


# A -> B, A  |=  B
MODUS_PONENS = [C("~A", "B"), C("A")]
GOAL_B = [C("~B")]  # the NEGATED goal, which is what a refutation needs


def test_symbols_are_sorted_and_deduplicated() -> None:
    # Sortedness is load-bearing, not cosmetic: the order fixes which bit each symbol occupies,
    # and therefore WHICH satisfying row is reported as the counterexample. Three symbols can
    # come out ordered by chance, so this uses eight.
    many = [C("~H", "C"), C("A", "F"), C("~D"), C("B", "~G"), C("E"), C("A")]
    assert symbols_of(many) == tuple("ABCDEFGH")
    assert symbols_of([]) == ()


# ------------------------------------------------------------------------------- the verdicts


def test_entailed() -> None:
    result = check(MODUS_PONENS, GOAL_B)
    assert result.verdict is Verdict.ENTAILED
    assert result.counterexample is None


def test_not_entailed_returns_a_counterexample() -> None:
    # Affirming the consequent: A -> B, B does NOT give A.
    result = check([C("~A", "B"), C("B")], [C("~A")])
    assert result.verdict is Verdict.NOT_ENTAILED
    assert result.counterexample == {"A": False, "B": True}


def test_inconsistent_premises() -> None:
    result = check([C("A"), C("~A")], [C("~B")])
    assert result.verdict is Verdict.INCONSISTENT_PREMISES
    # Checked BEFORE entailment, because a contradiction entails everything and reporting
    # "it follows!" would be true but useless.
    assert result.counterexample is None


def test_the_counterexample_really_satisfies_kb_and_the_negated_goal() -> None:
    # The property that makes the counterexample worth showing: it is a concrete situation in
    # which every premise holds and the conclusion fails.
    kb = [C("~A", "B"), C("B", "C")]
    negated_goal = [C("~A")]
    result = check(kb, negated_goal)
    assert result.verdict is Verdict.NOT_ENTAILED
    row = result.counterexample
    for clause in [*kb, *negated_goal]:
        satisfied = any((not row[lit[1:]]) if lit.startswith("~") else row[lit] for lit in clause)
        assert satisfied, f"{sorted(clause)} is false under the counterexample"


# ----------------------------------------------------------------------------- the edge cases


def test_tautological_conclusion_is_entailed_and_warned_about() -> None:
    # "A or not A" follows from anything, which is true but not what a student meant to ask.
    # The negation of a valid goal is unsatisfiable on its own.
    result = check([C("B")], [C("A"), C("~A")])
    assert result.verdict is Verdict.ENTAILED
    assert any("TAUTOLOGICAL_CONCLUSION" in w for w in result.warnings)


def test_an_empty_knowledge_base_is_consistent_not_an_error() -> None:
    # Nothing to contradict. The conclusion then follows only if it is itself valid.
    assert check([], [C("A"), C("~A")]).verdict is Verdict.ENTAILED
    assert check([], [C("~A")]).verdict is Verdict.NOT_ENTAILED


def test_a_goal_fact_absent_from_the_premises_does_not_follow() -> None:
    # Pairs with the CONCLUSION_FACT_UNSEEN warning from facts.py: that one flags the typo,
    # this one gives the honest verdict. A symbol no premise constrains can always be false.
    result = check([C("A")], [C("~Z")])
    assert result.verdict is Verdict.NOT_ENTAILED
    assert result.counterexample["Z"] is False


def test_too_many_facts_is_refused_rather_than_run() -> None:
    # 2**n rows: the cap is what keeps the method exhaustive AND fast. Exceeding it is a bug in
    # the caller, since facts.py enforces the same limit first.
    wide = [C(chr(ord("A") + i)) for i in range(11)]
    with pytest.raises(ParseError) as caught:
        check(wide, [C("~A")])
    assert caught.value.code is ErrorCode.TOO_MANY_FACTS


# ------------------------------------------------------------------- determinism and the bound


def test_counterexample_is_the_first_row_in_canonical_order() -> None:
    # Rows are a binary counter over sorted symbols, so the counterexample is reproducible on
    # any machine and in any process. "Some satisfying row" would make the message vary.
    #
    # This needs a case with SEVERAL satisfying rows, or first and last coincide and the test
    # proves nothing. A or B, concluding C: every row with C false and at least one of A, B
    # true qualifies, and counter order makes A=True, B=False, C=False the first of them.
    result = check([C("A", "B")], [C("~C")])
    assert result.verdict is Verdict.NOT_ENTAILED
    assert result.counterexample == {"A": True, "B": False, "C": False}


def test_repeated_calls_agree() -> None:
    kb = [C("~A", "B"), C("B", "C"), C("~C", "D")]
    first = check(kb, [C("~D")])
    assert first == check(kb, [C("~D")])
    assert isinstance(first, Entailment)


def test_worst_case_ten_facts_is_fast() -> None:
    # 1024 rows is the documented ceiling (HLD 6.4). Generous bound: this asserts the method is
    # not accidentally exponential in something else, not that the machine is fast.
    kb = [C(f"~{chr(ord('A') + i)}", chr(ord("A") + i + 1)) for i in range(9)]
    start = time.perf_counter()
    result = check([*kb, C("A")], [C("~J")])
    elapsed = time.perf_counter() - start
    assert result.verdict is Verdict.ENTAILED
    assert elapsed < 2.0, f"ten facts took {elapsed:.2f}s"
