"""Tests for core.fol_cnf -- the FOL CNF pipeline (HLD section 18.3).

Written before the implementation. This file covers Phase 2 (steps 1-3): eliminate_iff_implies,
push_negation_inward, standardize_variables. Phase 3 appends steps 4-8 and `to_fol_clauses` with
their own tests in this same file.

Each step's tests use the EXACT examples pinned in HLD section 18.3, because those are the
examples the design review already hand-verified -- re-deriving new ones risks testing a
different (and possibly also wrong) expectation than the one that was checked.
"""

import pytest
from src.core.fol_cnf import (
    distribute_and_over_or,
    drop_universal_quantifiers,
    eliminate_iff_implies,
    flatten_to_clauses,
    push_negation_inward,
    skolemize,
    standardize_apart_clauses,
    standardize_variables,
    to_fol_clauses,
)
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolIff,
    FolImplies,
    FolNot,
    FolOr,
    ForAll,
    FunctionTerm,
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


# -------------------------------------------------------------------------------- step 4: skolemize


def test_exists_with_no_enclosing_forall_becomes_a_skolem_constant() -> None:
    # HLD section 18.3 required test 1: Exists(y, P(y)) -> P[y -> c_sk0].
    assert skolemize(Exists(y, P(y))) == P(Constant("sk_c0"))


def test_exists_under_one_forall_becomes_a_function_of_it() -> None:
    # HLD section 18.3 required test 2: forall x exists y R(x,y) -> forall x R(x, sk_f0(x)).
    r_xy = Predicate("R", (x, y))
    expected = ForAll(x, Predicate("R", (x, FunctionTerm("sk_f0", (x,)))))
    assert skolemize(ForAll(x, Exists(y, r_xy))) == expected


def test_exists_under_two_foralls_is_a_function_of_both() -> None:
    # HLD section 18.3 required test 3: forall x forall z exists y R(x,z,y) -> sk_f0(x,z).
    r_xzy = Predicate("R", (x, z, y))
    f = ForAll(x, ForAll(z, Exists(y, r_xzy)))
    expected = ForAll(x, ForAll(z, Predicate("R", (x, z, FunctionTerm("sk_f0", (x, z))))))
    assert skolemize(f) == expected


def test_skolemize_increments_the_counter_across_several_existentials() -> None:
    f = FolAnd((Exists(x, P(x)), Exists(y, Q(y))))
    result = skolemize(f)
    assert result == FolAnd((P(Constant("sk_c0")), Q(Constant("sk_c1"))))


def test_skolemize_is_idempotent_on_a_formula_with_no_exists() -> None:
    f = ForAll(x, P(x))
    assert skolemize(f) == f


# ------------------------------------------------------------- step 5: drop_universal_quantifiers


def test_drop_strips_a_single_forall() -> None:
    assert drop_universal_quantifiers(ForAll(x, P(x))) == P(x)


def test_drop_strips_nested_foralls() -> None:
    assert drop_universal_quantifiers(ForAll(x, ForAll(y, Predicate("R", (x, y))))) == Predicate(
        "R", (x, y)
    )


def test_drop_recurses_through_connectives_around_quantifiers() -> None:
    f = FolAnd((ForAll(x, P(x)), ForAll(y, Q(y))))
    assert drop_universal_quantifiers(f) == FolAnd((P(x), Q(y)))


def test_drop_leaves_a_bare_predicate_unchanged() -> None:
    assert drop_universal_quantifiers(P(x)) == P(x)


# ----------------------------------------------------------------- step 6: distribute_and_over_or


def test_distribute_pushes_or_under_and() -> None:
    # (P & Q) | R  ->  (R | P) & (R | Q) -- same construction order core.cnf.distribute() uses:
    # the non-And branch (`rest`) comes first because it is what the loop already had in hand.
    f = FolOr((FolAnd((P(x), Q(x))), Predicate("R", (x,))))
    r = Predicate("R", (x,))
    assert distribute_and_over_or(f) == FolAnd((FolOr((r, P(x))), FolOr((r, Q(x)))))


def test_distribute_leaves_an_already_flat_disjunction_unchanged() -> None:
    f = FolOr((P(x), Q(x)))
    assert distribute_and_over_or(f) == f


def test_distribute_raises_over_the_clause_explosion_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.fol_cnf as fol_cnf

    monkeypatch.setattr(fol_cnf, "MAX_FOL_CLAUSES", 2)
    f = FolOr((FolAnd((P(x), Q(x), Predicate("R", (x,)))), Predicate("S", (x,))))
    with pytest.raises(fol_cnf.FolCNFExplosionError):
        distribute_and_over_or(f)


# --------------------------------------------------------------------- step 7: flatten_to_clauses


def test_flatten_splits_a_conjunction_into_one_clause_per_disjunction() -> None:
    f = FolAnd((FolOr((P(x), Q(x))), Predicate("R", (x,))))
    clauses = flatten_to_clauses(f)
    assert frozenset({(True, P(x)), (True, Q(x))}) in clauses
    assert frozenset({(True, Predicate("R", (x,)))}) in clauses
    assert len(clauses) == 2


def test_flatten_a_bare_negated_predicate_is_one_unit_clause() -> None:
    clauses = flatten_to_clauses(FolNot(P(x)))
    assert clauses == frozenset({frozenset({(False, P(x))})})


def test_flatten_rejects_a_node_that_is_not_a_literal() -> None:
    with pytest.raises(TypeError):
        flatten_to_clauses(FolOr((ForAll(x, P(x)), Q(x))))


# ------------------------------------------------------------- step 8: standardize_apart_clauses


def test_standardize_apart_gives_two_clauses_sharing_a_name_distinct_suffixes() -> None:
    # HLD section 18.3 step 8's own example: {(True, P(x))} and {(False, P(x))} must end up with
    # DIFFERENT renamings of x, even though each clause only ever saw one name.
    clause_a = frozenset({(True, P(x))})
    clause_b = frozenset({(False, P(x))})
    result = standardize_apart_clauses(frozenset({clause_a, clause_b}))
    assert len(result) == 2
    renamed_vars = {term.name for clause in result for _, pred in clause for term in pred.args}
    assert len(renamed_vars) == 2, f"expected two distinct renamings of x, got {renamed_vars}"


def test_standardize_apart_keeps_a_ground_clause_unchanged() -> None:
    ground = frozenset({(True, Predicate("Teaches", (Constant("alice"), Constant("bob"))))})
    assert standardize_apart_clauses(frozenset({ground})) == frozenset({ground})


def test_standardize_apart_renames_both_variables_in_one_clause_consistently() -> None:
    # A single clause with two literals sharing a variable must keep sharing it after renaming --
    # only the NAME changes, not whether two occurrences are the same variable.
    shared = frozenset({(True, P(x)), (False, Q(x))})
    (result,) = standardize_apart_clauses(frozenset({shared}))
    names = {term.name for _, pred in result for term in pred.args}
    assert len(names) == 1


def test_standardize_apart_is_deterministic_across_repeated_calls() -> None:
    clauses = frozenset({frozenset({(True, P(x))}), frozenset({(False, Predicate("Q", (y,)))})})
    assert standardize_apart_clauses(clauses) == standardize_apart_clauses(clauses)


# --------------------------------------------------------------------------- to_fol_clauses


def test_to_fol_clauses_socrates_premise() -> None:
    # HLD section 18.9 Test A: forall x (Human(x) -> Mortal(x)) clausifies to
    # {~Human(x), Mortal(x)}.
    human, mortal = Predicate("Human", (x,)), Predicate("Mortal", (x,))
    f = ForAll(x, FolImplies(human, mortal))
    (clause,) = to_fol_clauses(f)
    literals = {(polarity, pred.name) for polarity, pred in clause}
    assert literals == {(False, "Human"), (True, "Mortal")}


def test_to_fol_clauses_ground_fact_is_a_unit_clause() -> None:
    fact = Predicate("Human", (Constant("socrates"),))
    assert to_fol_clauses(fact) == frozenset({frozenset({(True, fact)})})


def test_to_fol_clauses_does_not_standardize_apart() -> None:
    # Deliberately NOT globally unique yet -- that is fol_prove's job (HLD section 18.6 step 3),
    # run once over every premise's clauses combined, not once per premise here. The variable
    # is standardize_variables' plain "v0", never standardize_apart_clauses' "c0_v0".
    f = ForAll(x, P(x))
    (clause,) = to_fol_clauses(f)
    ((_, pred),) = clause
    assert pred.args == (Variable("v0"),)


def test_to_fol_clauses_existential_produces_a_skolem_constant() -> None:
    (clause,) = to_fol_clauses(Exists(x, P(x)))
    ((polarity, pred),) = clause
    assert polarity is True
    assert isinstance(pred.args[0], Constant)
    assert pred.args[0].name.startswith("sk_c")
