"""Tests for core.unify -- the MGU and occurs check (HLD section 18.4).

Written before the implementation. Section 18.4.5's required-test table is reproduced exactly,
plus unify_literals and the Predicate/Predicate case the module docstring explains at length.
"""

from src.core.fol_models import Constant, FunctionTerm, Predicate, Variable
from src.core.unify import apply_subst, compose, occurs, unify, unify_literals

x, y = Variable("x"), Variable("y")
a, b = Constant("a"), Constant("b")


# ---------------------------------------------------------------------------------- occurs check


def test_occurs_true_when_variable_is_the_term_itself() -> None:
    assert occurs("x", x) is True


def test_occurs_false_for_an_unrelated_constant() -> None:
    assert occurs("x", a) is False


def test_occurs_true_inside_a_nested_function_term() -> None:
    assert occurs("x", FunctionTerm("f", (FunctionTerm("g", (x,)),))) is True


def test_occurs_false_when_absent_from_every_argument() -> None:
    assert occurs("x", FunctionTerm("f", (y, a))) is False


# ------------------------------------------------------------------------------------- apply_subst


def test_apply_subst_follows_a_two_step_chain() -> None:
    # x -> y, y -> a. Applying to x must give a directly, not the intermediate y.
    assert apply_subst(x, {"x": y, "y": a}) == a


def test_apply_subst_leaves_an_unbound_variable_alone() -> None:
    assert apply_subst(x, {"y": a}) == x


def test_apply_subst_recurses_into_function_term_arguments() -> None:
    assert apply_subst(FunctionTerm("f", (x,)), {"x": a}) == FunctionTerm("f", (a,))


# ---------------------------------------------------------------------------------------- compose


def test_compose_chains_a_variable_through_to_its_final_value() -> None:
    # x -> y via s1, y -> a via s2. compose(s1, s2) must map x directly to a.
    result = compose({"x": y}, {"y": a})
    assert result["x"] == a
    assert result["y"] == a


def test_compose_mutates_neither_argument() -> None:
    s1, s2 = {"x": y}, {"y": a}
    compose(s1, s2)
    assert s1 == {"x": y}
    assert s2 == {"y": a}


# ---------------------------------------------------------------- unify: HLD section 18.4.5 table


def test_unify_variable_against_constant() -> None:
    assert unify(x, a) == {"x": a}


def test_unify_variable_against_function_containing_itself_fails_occurs_check() -> None:
    assert unify(x, FunctionTerm("f", (x,))) is None


def test_unify_function_terms_with_matching_structure() -> None:
    assert unify(FunctionTerm("f", (x,)), FunctionTerm("f", (a,))) == {"x": a}


def test_unify_distinct_constants_fails() -> None:
    assert unify(a, b) is None


def test_unify_chains_two_bindings_through_compose() -> None:
    step1 = unify(x, y)
    assert step1 == {"x": y}
    step2 = unify(y, a, step1)
    assert step2 == {"x": y, "y": a}
    assert apply_subst(x, step2) == a


# --------------------------------------------------------------------------- unify: other cases


def test_unify_same_variable_against_itself_returns_subst_unchanged() -> None:
    assert unify(x, x) == {}
    assert unify(x, x, {"y": a}) == {"y": a}


def test_unify_function_terms_with_different_names_fails() -> None:
    assert unify(FunctionTerm("f", (x,)), FunctionTerm("g", (x,))) is None


def test_unify_function_terms_with_different_arity_fails() -> None:
    assert unify(FunctionTerm("f", (x,)), FunctionTerm("f", (x, y))) is None


def test_unify_respects_an_earlier_binding_within_the_same_call() -> None:
    # (x, x) vs (a, b): the second pair must fail because x is already bound to a.
    assert unify(FunctionTerm("f", (x, x)), FunctionTerm("f", (a, b))) is None


def test_unify_two_variables_binds_one_to_the_other() -> None:
    result = unify(x, y)
    assert result in ({"x": y}, {"y": x})


# --------------------------------------------------------------------- unify: Predicate/Predicate


def test_unify_predicates_same_name_and_arity() -> None:
    assert unify(Predicate("Human", (x,)), Predicate("Human", (a,))) == {"x": a}


def test_unify_predicates_different_name_fails() -> None:
    assert unify(Predicate("Human", (x,)), Predicate("Mortal", (x,))) is None


def test_unify_predicates_different_arity_fails() -> None:
    assert unify(Predicate("Teaches", (x, y)), Predicate("Teaches", (x,))) is None


def test_unify_predicates_multi_argument() -> None:
    # HLD section 18.9 Test E: Teaches(x,y) vs Teaches(alice,bob) -> {x: alice, y: bob}.
    alice, bob = Constant("alice"), Constant("bob")
    result = unify(Predicate("Teaches", (x, y)), Predicate("Teaches", (alice, bob)))
    assert result == {"x": alice, "y": bob}


# ------------------------------------------------------------------------------- unify_literals


def test_unify_literals_rejects_same_polarity() -> None:
    pos_a = (True, Predicate("Human", (x,)))
    pos_b = (True, Predicate("Human", (a,)))
    assert unify_literals(pos_a, pos_b) is None


def test_unify_literals_unifies_a_complementary_pair() -> None:
    pos = (True, Predicate("Human", (a,)))
    neg = (False, Predicate("Human", (x,)))
    assert unify_literals(pos, neg) == {"x": a}


def test_unify_literals_rejects_different_predicate_names_even_with_opposite_polarity() -> None:
    pos = (True, Predicate("Human", (x,)))
    neg = (False, Predicate("Mortal", (x,)))
    assert unify_literals(pos, neg) is None
