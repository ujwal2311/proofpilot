"""Tests for core.fol_resolve -- resolution with unification (HLD section 18.5).

Written before the implementation. Includes HLD section 18.9 Test A (Socrates) and Test E
(Teaches/Knows) worked step by step, exactly as the design review hand-verified them, plus the
soundness property the module docstring calls out explicitly: the MGU must apply to every
surviving literal, not only the ones from whichever parent held the pivot.
"""

from src.core.fol_models import Constant, FunctionTerm, Predicate, Variable
from src.core.fol_resolve import apply_literal_subst, canonical_clause, is_tautology_fol, resolve

x, y = Variable("x"), Variable("y")
socrates, alice, bob = Constant("socrates"), Constant("alice"), Constant("bob")


def human(t: object) -> Predicate:
    return Predicate("Human", (t,))  # type: ignore[arg-type]


def mortal(t: object) -> Predicate:
    return Predicate("Mortal", (t,))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- apply_literal_subst


def test_apply_literal_subst_rewrites_every_term_and_keeps_polarity() -> None:
    literal = (False, human(x))
    assert apply_literal_subst(literal, {"x": socrates}) == (False, human(socrates))


def test_apply_literal_subst_recurses_into_function_terms() -> None:
    pred = Predicate("Loves", (x, FunctionTerm("sk_f0", (x,))))
    result = apply_literal_subst((True, pred), {"x": alice})
    assert result == (True, Predicate("Loves", (alice, FunctionTerm("sk_f0", (alice,)))))


# ------------------------------------------------------------------------------- is_tautology_fol


def test_is_tautology_true_for_a_literal_and_its_exact_negation() -> None:
    clause = frozenset({(True, human(socrates)), (False, human(socrates))})
    assert is_tautology_fol(clause) is True


def test_is_tautology_false_when_terms_merely_could_be_unified() -> None:
    # (True, Human(x)) and (False, Human(socrates)) are NOT yet syntactically equal -- no further
    # unification is attempted by this check (HLD section 18.5).
    clause = frozenset({(True, human(x)), (False, human(socrates))})
    assert is_tautology_fol(clause) is False


def test_is_tautology_false_for_an_ordinary_clause() -> None:
    clause = frozenset({(False, human(x)), (True, mortal(x))})
    assert is_tautology_fol(clause) is False


def test_is_tautology_false_for_the_empty_clause() -> None:
    assert is_tautology_fol(frozenset()) is False


# ------------------------------------------------------------------------------------------ resolve


def test_resolve_socrates_step_one() -> None:
    # HLD section 18.9 Test A, step 1: {~Human(x), Mortal(x)} + {Human(socrates)}
    #                                  -> {Mortal(socrates)}, via x -> socrates.
    clause_a = frozenset({(False, human(x)), (True, mortal(x))})
    clause_b = frozenset({(True, human(socrates))})
    assert resolve(clause_a, clause_b) == [frozenset({(True, mortal(socrates))})]


def test_resolve_socrates_step_two_derives_the_empty_clause() -> None:
    # HLD section 18.9 Test A, step 2: {Mortal(socrates)} + {~Mortal(socrates)} -> {} (PROVED).
    clause_a = frozenset({(True, mortal(socrates))})
    clause_b = frozenset({(False, mortal(socrates))})
    assert resolve(clause_a, clause_b) == [frozenset()]


def test_resolve_teaches_knows_multi_argument() -> None:
    # HLD section 18.9 Test E, step 1: {~Teaches(x,y), Knows(y,x)} + {Teaches(alice,bob)}
    #                                  -> {Knows(bob,alice)}, via x->alice, y->bob.
    teaches_xy = Predicate("Teaches", (x, y))
    knows_yx = Predicate("Knows", (y, x))
    clause_a = frozenset({(False, teaches_xy), (True, knows_yx)})
    clause_b = frozenset({(True, Predicate("Teaches", (alice, bob)))})
    assert resolve(clause_a, clause_b) == [frozenset({(True, Predicate("Knows", (bob, alice)))})]


def test_resolve_returns_no_pivot_when_no_literals_are_complementary() -> None:
    clause_a = frozenset({(True, human(x))})
    clause_b = frozenset({(True, mortal(x))})
    assert resolve(clause_a, clause_b) == []


def test_resolve_skips_a_pivot_whose_predicates_do_not_unify() -> None:
    clause_a = frozenset({(True, human(socrates))})
    clause_b = frozenset({(False, human(alice))})
    assert resolve(clause_a, clause_b) == []


def test_resolve_filters_a_tautological_resolvent() -> None:
    # {P(x), Q(a)} + {~P(b), Q(a)} resolving on P: {Q(a), Q(a)} after x->b is not a tautology by
    # itself -- construct a genuine tautology instead: {P(x), R(a)} + {~P(a), R(a)}'s pivot
    # produces {R(a), R(a)} = {R(a)} (fine); use a case that actually yields a tautology:
    # {P(x), Q(x)} + {~P(a), ~Q(a)} resolving on P gives {Q(a), ~Q(a)} -- a tautology.
    p, q = Predicate("P", (x,)), Predicate("Q", (x,))
    a = Constant("a")
    clause_a = frozenset({(True, p), (True, q)})
    clause_b = frozenset({(False, Predicate("P", (a,))), (False, Predicate("Q", (a,)))})
    assert resolve(clause_a, clause_b) == []


def test_resolve_soundness_applies_the_mgu_to_every_surviving_literal() -> None:
    # {~Human(x), Mortal(x), Wise(x)} + {Human(socrates)}: the MGU x->socrates must hit BOTH
    # surviving literals from clause_a (Mortal AND Wise), not just the pivot's own clause's first
    # one. The classic unsound-implementation bug leaves Wise(x) un-substituted.
    clause_a = frozenset({(False, human(x)), (True, mortal(x)), (True, Predicate("Wise", (x,)))})
    clause_b = frozenset({(True, human(socrates))})
    (resolvent,) = resolve(clause_a, clause_b)
    assert resolvent == frozenset(
        {(True, mortal(socrates)), (True, Predicate("Wise", (socrates,)))}
    )


def test_resolve_can_produce_several_resolvents_from_several_pivots() -> None:
    # Two independent complementary pairs (P/P and Q/Q, different constants on each side) so
    # neither resolvent collapses into a tautology -- unlike same-constant Human/Mortal pairs,
    # which resolve back into a tautology on BOTH pivots and would make this test vacuous.
    p_x, q_y = Predicate("P", (x,)), Predicate("Q", (y,))
    p_a = Predicate("P", (Constant("a"),))
    q_b = Predicate("Q", (Constant("b"),))
    clause_a = frozenset({(True, p_x), (True, q_y)})
    clause_b = frozenset({(False, p_a), (False, q_b)})
    results = resolve(clause_a, clause_b)
    assert len(results) == 2
    assert all(not is_tautology_fol(r) for r in results)


# -------------------------------------------------------------------------------- canonical_clause


def test_canonical_clause_is_order_independent() -> None:
    clause = frozenset({(True, human(x)), (False, mortal(x))})
    assert canonical_clause(clause) == canonical_clause(frozenset(reversed(list(clause))))


def test_canonical_clause_distinguishes_different_clauses() -> None:
    a = frozenset({(True, human(x))})
    b = frozenset({(False, human(x))})
    assert canonical_clause(a) != canonical_clause(b)
