"""Tests for core.fol_cnf -- the FOL CNF pipeline (HLD section 18.3).

Written before the implementation. This file covers Phase 2 (steps 1-3): eliminate_iff_implies,
push_negation_inward, standardize_variables. Phase 3 appends steps 4-8 and `to_fol_clauses` with
their own tests in this same file.

Each step's tests use the EXACT examples pinned in HLD section 18.3, because those are the
examples the design review already hand-verified -- re-deriving new ones risks testing a
different (and possibly also wrong) expectation than the one that was checked.
"""

from src.core.fol_cnf import eliminate_iff_implies, push_negation_inward, standardize_variables
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolIff,
    FolImplies,
    FolNot,
    FolOr,
    ForAll,
    Predicate,
    Variable,
)

x, y, z = Variable("x"), Variable("y"), Variable("z")


def P(*args: object) -> Predicate:
    return Predicate("P", args)  # type: ignore[arg-type]


def Q(*args: object) -> Predicate:
    return Predicate("Q", args)  # type: ignore[arg-type]


# ----------------------------------------------------------------- step 1: eliminate_iff_implies


def test_eliminate_implies_becomes_or_not() -> None:
    assert eliminate_iff_implies(FolImplies(P(x), Q(x))) == FolOr((FolNot(P(x)), Q(x)))


def test_eliminate_iff_becomes_and_of_two_implications_as_or() -> None:
    result = eliminate_iff_implies(FolIff(P(x), Q(x)))
    assert result == FolAnd((FolOr((FolNot(P(x)), Q(x))), FolOr((FolNot(Q(x)), P(x)))))


def test_eliminate_recurses_into_quantifier_bodies() -> None:
    f = ForAll(x, FolImplies(P(x), Q(x)))
    assert eliminate_iff_implies(f) == ForAll(x, FolOr((FolNot(P(x)), Q(x))))


def test_eliminate_leaves_a_bare_predicate_unchanged() -> None:
    assert eliminate_iff_implies(P(x)) == P(x)


def test_eliminate_output_contains_no_implies_or_iff_even_when_nested() -> None:
    f = FolIff(FolImplies(P(x), Q(x)), P(y))
    result = eliminate_iff_implies(f)

    def _has_implies_or_iff(node: object) -> bool:
        if isinstance(node, FolImplies | FolIff):
            return True
        if isinstance(node, FolAnd | FolOr):
            return any(_has_implies_or_iff(i) for i in node.items)
        if isinstance(node, FolNot):
            return _has_implies_or_iff(node.body)
        return False

    assert not _has_implies_or_iff(result)


# ------------------------------------------------------------------- step 2: push_negation_inward


def test_double_negation_cancels() -> None:
    assert push_negation_inward(FolNot(FolNot(P(x)))) == P(x)


def test_de_morgan_not_and_becomes_or_of_nots() -> None:
    assert push_negation_inward(FolNot(FolAnd((P(x), Q(x))))) == FolOr((FolNot(P(x)), FolNot(Q(x))))


def test_de_morgan_not_or_becomes_and_of_nots() -> None:
    assert push_negation_inward(FolNot(FolOr((P(x), Q(x))))) == FolAnd((FolNot(P(x)), FolNot(Q(x))))


def test_quantifier_de_morgan_not_forall_becomes_exists_not() -> None:
    # HLD section 18.3's own pinned example -- the case 90% of implementations get wrong.
    assert push_negation_inward(FolNot(ForAll(x, P(x)))) == Exists(x, FolNot(P(x)))


def test_quantifier_de_morgan_not_exists_becomes_forall_not() -> None:
    assert push_negation_inward(FolNot(Exists(x, P(x)))) == ForAll(x, FolNot(P(x)))


def test_quantifier_de_morgan_nests_correctly_two_levels_deep() -> None:
    # Not(ForAll(x, Exists(y, P(x,y)))) -> Exists(x, Not(Exists(y, P(x,y))))
    #                                    -> Exists(x, ForAll(y, Not(P(x,y))))
    f = FolNot(ForAll(x, Exists(y, P(x, y))))
    assert push_negation_inward(f) == Exists(x, ForAll(y, FolNot(P(x, y))))


def test_negated_predicate_is_the_base_case_and_is_kept() -> None:
    assert push_negation_inward(FolNot(P(x))) == FolNot(P(x))


def test_push_negation_recurses_through_quantifiers_with_no_negation() -> None:
    assert push_negation_inward(ForAll(x, Exists(y, P(x, y)))) == ForAll(x, Exists(y, P(x, y)))


# ----------------------------------------------------------------- step 3: standardize_variables


def test_nested_forall_reusing_a_variable_name_gets_distinct_fresh_names() -> None:
    # HLD section 18.3 required test 1: forall x (P(x) and forall x Q(x)) -> forall v0 (P(v0) and
    # forall v1 Q(v1)). The inner, shadowing x must NOT be renamed by the outer x's substitution.
    f = ForAll(x, FolAnd((P(x), ForAll(x, Q(x)))))
    v0, v1 = Variable("v0"), Variable("v1")
    assert standardize_variables(f) == ForAll(v0, FolAnd((P(v0), ForAll(v1, Q(v1)))))


def test_mixed_forall_exists_nesting_each_get_a_fresh_name() -> None:
    # HLD section 18.3 required test 2: forall x exists y R(x,y) -> forall v0 exists v1 R(v0,v1).
    r_xy = Predicate("R", (x, y))
    v0, v1 = Variable("v0"), Variable("v1")
    expected = ForAll(v0, Exists(v1, Predicate("R", (v0, v1))))
    assert standardize_variables(ForAll(x, Exists(y, r_xy))) == expected


def test_free_variables_are_left_untouched() -> None:
    # HLD section 18.3 required test 3: a variable with no enclosing quantifier is not renamed.
    assert standardize_variables(P(z)) == P(z)


def test_a_fresh_counter_restarts_numbering_from_zero() -> None:
    v0 = Variable("v0")
    assert standardize_variables(ForAll(x, P(x))) == ForAll(v0, P(v0))
    assert standardize_variables(ForAll(y, Q(y))) == ForAll(v0, Q(v0))


def test_a_shared_counter_does_not_restart_between_calls() -> None:
    # Required so to_fol_clauses() (Phase 3) can standardize several premises without two of
    # them independently reusing v0 and silently capturing each other's variables.
    counter = [0]
    first = standardize_variables(ForAll(x, P(x)), counter)
    second = standardize_variables(ForAll(y, Q(y)), counter)
    assert first == ForAll(Variable("v0"), P(Variable("v0")))
    assert second == ForAll(Variable("v1"), Q(Variable("v1")))


def test_standardize_recurses_into_connectives_around_quantifiers() -> None:
    f = FolAnd((ForAll(x, P(x)), ForAll(x, Q(x))))
    v0, v1 = Variable("v0"), Variable("v1")
    assert standardize_variables(f) == FolAnd((ForAll(v0, P(v0)), ForAll(v1, Q(v1))))


def test_standardize_preserves_a_constant_argument_unchanged() -> None:
    socrates = Constant("socrates")
    f = ForAll(x, FolImplies(Predicate("Human", (x,)), Predicate("Mortal", (x,))))
    result = standardize_variables(FolAnd((f, Predicate("Human", (socrates,)))))
    assert Predicate("Human", (socrates,)) in result.items
