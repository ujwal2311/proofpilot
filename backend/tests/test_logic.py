"""Tests for core.logic -- resolution and step diagnosis (docs/HLD.md section 6.7).

Written before the implementation. Fixtures are literals, never files: core reads nothing
from disk (HLD v2.4), so every case here is constructed inline.
"""

import pytest
from src.core.logic import Clause, Code, canonical, diagnose, negate, normalize_literal, resolvents


def C(*literals: str) -> Clause:
    """Build a clause. Keeps the fixtures below readable."""
    return frozenset(literals)


EMPTY = C()


# --------------------------------------------------------------------------- normalize_literal
# Not in the HLD's named test list, which is a gap its own traceability table records as PARTIAL
# ("normalize_literal accepts ~P, the unicode negation, ' ~ p '" -- no test named). Added here.


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("P", "P"),
        ("p", "P"),
        ("  p  ", "P"),
        ("~P", "~P"),
        ("~p", "~P"),
        (" ~ p ", "~P"),
        ("¬P", "~P"),  # unicode NOT sign
        (" ¬ p ", "~P"),
    ],
)
def test_normalize_literal_accepts_documented_forms(raw: str, expected: str) -> None:
    assert normalize_literal(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",  # nothing
        "   ",  # whitespace only
        "~",  # negation with no symbol
        "PQ",  # two symbols
        "1",  # not a letter
        "~1",
        "~~P",  # double negation is not a literal -- reject, never silently simplify
        "!P",  # undocumented negation marker
        "not P",  # English belongs to english.py, not here
    ],
)
def test_normalize_literal_rejects_malformed(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_literal(raw)


def test_negate_is_an_involution() -> None:
    for lit in ("P", "~P", "Z"):
        assert negate(negate(lit)) == lit
    assert negate("P") == "~P"
    assert negate("~P") == "P"


def test_canonical_is_sorted_and_order_independent() -> None:
    # The guard against hash-order nondeterminism (HLD section 17.10).
    #
    # Comparing two equal frozensets is NOT enough: equal frozensets iterate identically within
    # a process, so `tuple(clause)` would satisfy it and the guard would be decorative. The real
    # assertion is that the output is *sorted*. Eight literals are used because a broken
    # implementation would then have to hit sorted order by chance (1 in 8!), across two fixed
    # hash seeds and four CI jobs.
    literals = ["Z", "A", "M", "~B", "~Y", "C", "D", "~E"]
    assert canonical(frozenset(literals)) == tuple(sorted(literals))
    assert canonical(C("~Q", "P")) == canonical(C("P", "~Q"))
    assert canonical(EMPTY) == ()


# ---------------------------------------------------------------------------------- resolvents


def test_resolve_single_clash() -> None:
    a, b = C("P", "Q"), C("~P", "R")
    assert resolvents(a, b) == {C("Q", "R")}


def test_resolve_unit_clauses_gives_the_empty_clause() -> None:
    assert resolvents(C("P"), C("~P")) == {EMPTY}


def test_resolve_without_a_clash_is_empty() -> None:
    assert resolvents(C("P", "Q"), C("R", "S")) == frozenset()


def test_two_clashes_yield_only_tautologies() -> None:
    # The property the whole diagnosis order rests on: with two or more complementary pairs,
    # every single-pivot resolvent must retain the other pair, so it is a tautology. This is why
    # WRONG_RESOLVENT can only be reached with exactly one pivot, hence exactly one correct
    # answer and no ambiguity in "missing/extra".
    a, b = C("P", "Q", "R"), C("~P", "~Q")
    produced = resolvents(a, b)
    assert produced == {C("Q", "R", "~Q"), C("P", "R", "~P")}
    for clause in produced:
        assert any(negate(lit) in clause for lit in clause), (
            f"{canonical(clause)} is not a tautology"
        )


# ------------------------------------------------------------------------------------ diagnose

# One fixture per code, exercising the documented order. `existing` always includes the parents,
# which is harmless: a resolvent drops its pivot, so it can never equal a parent that carries it.
A1, B1 = C("P", "Q"), C("~P", "R")  # exactly one pivot (P); correct resolvent {Q, R}
A2, B2 = C("P", "Q", "R"), C("~P", "~Q")  # two pivots; double-cancel leaves {R}
A3, B3 = C("P", "Q"), C("~P", "~Q")  # two pivots; double-cancel leaves the empty clause


@pytest.mark.parametrize(
    ("a", "b", "claimed", "existing", "expected"),
    [
        # No complementary pair at all -- checked first, so the claim is never even considered.
        (C("P", "Q"), C("R", "S"), C("P", "Q", "R", "S"), frozenset(), Code.NO_CLASH),
        # Both pairs cancelled in one step.
        (A2, B2, C("R"), frozenset({A2, B2}), Code.DOUBLE_CANCEL),
        # Right pivot, wrong literals: {R} dropped, {S} invented.
        (A1, B1, C("Q", "S"), frozenset({A1, B1}), Code.WRONG_RESOLVENT),
        # A legitimate single-pivot resolvent that happens to be a tautology.
        (A3, B3, C("Q", "~Q"), frozenset({A3, B3}), Code.TAUTOLOGY),
        # Correct, but this clause is already on the board.
        (A1, B1, C("Q", "R"), frozenset({A1, B1, C("Q", "R")}), Code.DUPLICATE),
        (A1, B1, C("Q", "R"), frozenset({A1, B1}), Code.VALID),
    ],
)
def test_diagnose_all_six_codes(
    a: Clause, b: Clause, claimed: Clause, existing: frozenset[Clause], expected: Code
) -> None:
    assert diagnose(a, b, claimed, existing).code is expected


def test_diagnose_wrong_resolvent_lists_missing_and_extra() -> None:
    result = diagnose(A1, B1, C("Q", "S"), frozenset({A1, B1}))
    assert result.code is Code.WRONG_RESOLVENT
    assert result.missing == C("R"), "R belongs in the resolvent and was omitted"
    assert result.extra == C("S"), "S was invented"


def test_diagnose_reports_nothing_missing_or_extra_unless_wrong_resolvent() -> None:
    for a, b, claimed, existing in [
        (C("P", "Q"), C("R", "S"), C("P"), frozenset()),
        (A1, B1, C("Q", "R"), frozenset({A1, B1})),
        (A2, B2, C("R"), frozenset({A2, B2})),
    ]:
        result = diagnose(a, b, claimed, existing)
        assert result.missing == frozenset()
        assert result.extra == frozenset()


def test_diagnose_double_cancel_beats_wrong_resolvent() -> None:
    # {R} is not a single-pivot resolvent of A2/B2, so without the DOUBLE_CANCEL check it would
    # be reported as WRONG_RESOLVENT -- a far less useful message than naming the actual mistake.
    assert diagnose(A2, B2, C("R"), frozenset({A2, B2})).code is Code.DOUBLE_CANCEL


def test_diagnose_double_cancel_can_produce_the_empty_clause() -> None:
    # The dangerous case: cancelling both pairs of {P,Q} and {~P,~Q} "reaches" the empty clause
    # and would end the proof on a bad step if it were accepted.
    assert diagnose(A3, B3, EMPTY, frozenset({A3, B3})).code is Code.DOUBLE_CANCEL


def test_diagnose_partial_double_cancel_with_three_pivots() -> None:
    # Two of three pairs cancelled: still DOUBLE_CANCEL. The spec says "2+ pairs removed",
    # not "all pairs".
    a, b = C("P", "Q", "R", "S"), C("~P", "~Q", "~R")
    assert diagnose(a, b, C("S", "R", "~R"), frozenset({a, b})).code is Code.DOUBLE_CANCEL


def test_diagnose_empty_clause_is_an_ordinary_valid_resolvent() -> None:
    a, b = C("P"), C("~P")
    assert diagnose(a, b, EMPTY, frozenset({a, b})).code is Code.VALID


def test_diagnose_is_order_independent_in_its_arguments() -> None:
    # Clause order must not change the verdict; the student picks two cards, not an ordered pair.
    assert diagnose(A1, B1, C("Q", "R"), frozenset()).code is Code.VALID
    assert diagnose(B1, A1, C("Q", "R"), frozenset()).code is Code.VALID
