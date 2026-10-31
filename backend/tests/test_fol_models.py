"""Tests for core.fol_models -- the FOL data model (HLD section 18.1).

Written before the implementation (Phase 1 of the FOL sprint, HLD section 18.12).

CONTRACT under test:
  1. Every type is a FROZEN dataclass -- mutation must raise, not silently succeed.
  2. Structural equality: two terms/predicates/literals built from equal parts compare equal
     and hash equal, because `unify` and `fol_resolve` (later phases) rely on that to deduplicate
     clauses and look up literals.
  3. `FolClause = frozenset[FolLiteral]` is hashable, since the BFS visited set needs it.
  4. Quantifier order is preserved as distinct trees -- `ForAll(x, Exists(y, ...))` must not
     equal `Exists(y, ForAll(x, ...))`.
  5. `FunctionTerm.args` and `Predicate.args` round-trip through equality/hash when they nest.
"""

import dataclasses

import pytest
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolClause,
    FolIff,
    FolImplies,
    FolNot,
    FolOr,
    ForAll,
    FunctionTerm,
    Predicate,
    Variable,
)

DATACLASSES = (
    Variable,
    Constant,
    FunctionTerm,
    Predicate,
    FolNot,
    FolAnd,
    FolOr,
    FolImplies,
    FolIff,
    ForAll,
    Exists,
)


@pytest.mark.parametrize("cls", DATACLASSES)
def test_every_type_is_frozen(cls: type) -> None:
    assert dataclasses.is_dataclass(cls)
    assert cls.__dataclass_params__.frozen


def test_variable_and_constant_are_distinguished_by_type_not_just_name() -> None:
    assert Variable("x") != Constant("x")
    assert hash(Variable("x")) != hash(Constant("x")) or Variable("x") != Constant("x")


def test_equal_terms_compare_and_hash_equal() -> None:
    a = FunctionTerm("sk_f0", (Variable("x"), Constant("alice")))
    b = FunctionTerm("sk_f0", (Variable("x"), Constant("alice")))
    assert a == b
    assert hash(a) == hash(b)


def test_function_term_mutation_raises() -> None:
    term = FunctionTerm("f", (Variable("x"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        term.name = "g"  # type: ignore[misc]


def test_predicate_zero_arity_is_the_propositional_bridge() -> None:
    atom = Predicate("P", ())
    assert atom.args == ()
    assert hash(atom) == hash(Predicate("P", ()))


def test_fol_literal_is_a_polarity_predicate_pair() -> None:
    pos = (True, Predicate("Human", (Constant("socrates"),)))
    neg = (False, Predicate("Human", (Constant("socrates"),)))
    assert pos != neg
    assert pos[1] == neg[1]


def test_fol_clause_is_a_hashable_frozenset_of_literals() -> None:
    clause: FolClause = frozenset(
        {
            (False, Predicate("Human", (Variable("x"),))),
            (True, Predicate("Mortal", (Variable("x"),))),
        }
    )
    assert isinstance(hash(clause), int)
    # Membership and equality must survive a round trip through a set, exactly as the BFS
    # visited set in fol_search.py (Phase 7) will rely on.
    seen = {clause}
    assert clause in seen


def test_quantifier_order_is_preserved_as_distinct_trees() -> None:
    x, y = Variable("x"), Variable("y")
    loves_xy = Predicate("Loves", (x, y))
    for_all_exists = ForAll(x, Exists(y, loves_xy))
    exists_for_all = Exists(y, ForAll(x, loves_xy))
    assert for_all_exists != exists_for_all


def test_connective_nodes_nest_and_compare_structurally() -> None:
    p, q = Predicate("P", ()), Predicate("Q", ())
    left = FolAnd((FolNot(p), FolOr((p, q))))
    right = FolAnd((FolNot(p), FolOr((p, q))))
    assert left == right
    assert FolImplies(p, q) != FolImplies(q, p)
    assert FolIff(p, q) == FolIff(p, q)


def test_fol_prefixed_names_do_not_collide_with_english_node_names() -> None:
    # HLD S18.1: the Fol prefix exists so core.english's Not/And/Or/Implies/Iff and these FOL
    # connectives can be imported side by side without a name clash.
    from src.core import english

    assert not hasattr(english, "FolNot")
    assert not hasattr(english, "FolAnd")
