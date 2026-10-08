"""Tests for core.cnf -- AST to clause form (docs/HLD.md sections 6.2, 17.3).

Written before the implementation. The centrepiece is the equivalence property: CNF conversion
must preserve meaning on EVERY assignment, not merely satisfiability. A per-production table
catches the cases a reader would check by hand; the property test catches the ones nobody thinks
of.
"""

import random

import pytest
from src.core.cnf import distribute, eliminate, goal_clauses, premise_clauses, push_negation
from src.core.english import And, Atom, Iff, Implies, Not, Or, parse_sentence
from src.core.logic import canonical

# The parser lowercases, so the clearest literal_of for single-letter fixtures just uppercases.
IDENT = str.upper


def clauses(sentence: str, literal_of=IDENT) -> list[tuple[str, ...]]:
    """Parse, convert and render canonically, so expectations read like the HLD's tables."""
    return [canonical(c) for c in premise_clauses(parse_sentence(sentence), literal_of)]


# ------------------------------------------------------------------- every grammar production


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        # The nine meanings from HLD 3.3, each with the clausal form that table states.
        ("if A then B", [("B", "~A")]),
        ("B if A", [("B", "~A")]),
        ("A only if B", [("B", "~A")]),
        ("A unless B", [("A", "B")]),
        ("either A or B", [("A", "B")]),
        ("neither A nor B", [("~A",), ("~B",)]),
        ("A if and only if B", [("A", "~B"), ("B", "~A")]),
        ("both A and B", [("A",), ("B",)]),
        ("A and B", [("A",), ("B",)]),
        ("A or B", [("A", "B")]),
        ("A", [("A",)]),
        ("it is not the case that A", [("~A",)]),
        # The compound forms from HLD 17.2.
        ("if A and B then C", [("C", "~A", "~B")]),
        ("if A or B then C", [("C", "~A"), ("C", "~B")]),
        ("if A then B and C", [("B", "~A"), ("C", "~A")]),
        ("if A then B or C", [("B", "C", "~A")]),
    ],
)
def test_every_production_through_cnf(sentence: str, expected) -> None:
    assert clauses(sentence) == sorted(expected)


def test_literal_of_carries_polarity() -> None:
    # cnf.py knows nothing about facts: the caller supplies the mapping, and a negative fact is
    # just a literal that happens to start with "~".
    # A->B is ~A v B; with A mapped to the NEGATIVE literal ~P, that ~A becomes P.
    assert clauses("if A then B", {"a": "~P", "b": "Q"}.get) == [("P", "Q")]


# ------------------------------------------------------------------------ the three steps


def test_eliminate_removes_implications_and_biconditionals() -> None:
    assert eliminate(Implies(Atom("A"), Atom("B"))) == Or((Not(Atom("A")), Atom("B")))
    assert eliminate(Iff(Atom("A"), Atom("B"))) == And(
        (Or((Not(Atom("A")), Atom("B"))), Or((Not(Atom("B")), Atom("A"))))
    )


def test_push_negation_applies_de_morgan_both_ways() -> None:
    assert push_negation(Not(And((Atom("A"), Atom("B"))))) == Or((Not(Atom("A")), Not(Atom("B"))))
    assert push_negation(Not(Or((Atom("A"), Atom("B"))))) == And((Not(Atom("A")), Not(Atom("B"))))


def test_push_negation_cancels_double_negation() -> None:
    assert push_negation(Not(Not(Atom("A")))) == Atom("A")
    assert push_negation(Not(Not(Not(Atom("A"))))) == Not(Atom("A"))


def test_distribute_pushes_or_under_and() -> None:
    # A ∨ (B ∧ C)  ==  (A ∨ B) ∧ (A ∨ C)
    assert distribute(Or((Atom("A"), And((Atom("B"), Atom("C")))))) == And(
        (Or((Atom("A"), Atom("B"))), Or((Atom("A"), Atom("C"))))
    )


# --------------------------------------------------------------- tautologies and duplicates


def test_tautologies_are_dropped() -> None:
    # (A ∨ ¬A) is always true, so dropping it cannot change what the clause set means.
    assert premise_clauses(Or((Atom("A"), Not(Atom("A")))), IDENT) == []
    assert clauses("if A then A") == []


def test_duplicate_clauses_are_dropped() -> None:
    assert clauses("A and A") == [("A",)]
    assert clauses("if A then B and B") == [("B", "~A")]


def test_clause_order_is_canonical_and_stable() -> None:
    # Two clauses can come out sorted by luck, and comparing two calls in one process proves
    # nothing because equal sets iterate identically there. The 25-clause worst case makes an
    # unsorted implementation essentially impossible to miss.
    result = clauses("if " + " or ".join("ABCDE") + " then " + " and ".join("FGHIJ"))
    assert len(result) == 25
    assert result == sorted(result)


def test_nested_junctions_are_flattened() -> None:
    # distribute() can build Or-inside-Or while rewriting, and a clause must end up as ONE flat
    # disjunction. Constructed directly, because the parser's flat grammar never nests.
    nested = Or((Or((Atom("A"), Atom("B"))), Atom("C")))
    assert distribute(nested) == Or((Atom("A"), Atom("B"), Atom("C")))
    assert [canonical(c) for c in premise_clauses(nested, IDENT)] == [("A", "B", "C")]

    deep = And((And((Atom("A"), Atom("B"))), Atom("C")))
    assert [canonical(c) for c in premise_clauses(deep, IDENT)] == [("A",), ("B",), ("C",)]


def test_distribute_unwraps_a_single_operand() -> None:
    # A one-item And or Or is not a junction, it is the operand itself. distribute() returns a
    # NORMALISED formula, so downstream code can match on node type without having to peel
    # wrappers first. The parser never builds these, so only a direct call reaches it.
    assert distribute(And((Atom("A"),))) == Atom("A")
    assert distribute(Or((Atom("A"),))) == Atom("A")
    assert distribute(And((Or((Atom("A"), Atom("B"))),))) == Or((Atom("A"), Atom("B")))


# ------------------------------------------------------------------------- negating the goal


def test_goal_clauses_negate_a_conjunctive_conclusion() -> None:
    # ¬(A ∧ B) = ¬A ∨ ¬B -- ONE clause. A refutation needs the negated goal, not the goal.
    assert [canonical(c) for c in goal_clauses(parse_sentence("A and B"), IDENT)] == [("~A", "~B")]


def test_goal_clauses_negate_a_disjunctive_conclusion() -> None:
    # ¬(A ∨ B) = ¬A ∧ ¬B -- TWO clauses.
    assert [canonical(c) for c in goal_clauses(parse_sentence("A or B"), IDENT)] == [
        ("~A",),
        ("~B",),
    ]


def test_goal_clauses_negate_an_atom_and_an_implication() -> None:
    assert [canonical(c) for c in goal_clauses(parse_sentence("A"), IDENT)] == [("~A",)]
    # ¬(A → B) = A ∧ ¬B
    assert [canonical(c) for c in goal_clauses(parse_sentence("if A then B"), IDENT)] == [
        ("A",),
        ("~B",),
    ]


# ------------------------------------------------------------------------- the size bound


def test_worst_case_production_stays_within_the_documented_bound() -> None:
    # HLD 6.2: (A1∨…∨Am) → (B1∧…∧Bn) yields exactly m×n clauses, and m+n ≤ 10 facts caps it at
    # 25. This is why general CNF conversion is safe here despite its reputation.
    antecedent = " or ".join("ABCDE")
    consequent = " and ".join("FGHIJ")
    produced = clauses(f"if {antecedent} then {consequent}")
    assert len(produced) == 25
    assert len(produced) <= 25


# ----------------------------------------------------------------- the equivalence property


def _symbols(literal_of, phrases) -> list[str]:
    return sorted({literal_of(p).lstrip("~") for p in phrases})


def _eval_ast(node, assignment, literal_of) -> bool:
    match node:
        case Atom(phrase):
            literal = literal_of(phrase)
            value = assignment[literal.lstrip("~")]
            return not value if literal.startswith("~") else value
        case Not(item):
            return not _eval_ast(item, assignment, literal_of)
        case And(items):
            return all(_eval_ast(i, assignment, literal_of) for i in items)
        case Or(items):
            return any(_eval_ast(i, assignment, literal_of) for i in items)
        case Implies(antecedent, consequent):
            return (not _eval_ast(antecedent, assignment, literal_of)) or _eval_ast(
                consequent, assignment, literal_of
            )
        case Iff(left, right):
            return _eval_ast(left, assignment, literal_of) == _eval_ast(
                right, assignment, literal_of
            )
    raise AssertionError(f"unevaluable node: {node!r}")


def _eval_clauses(clause_list, assignment) -> bool:
    return all(
        any((not assignment[lit[1:]]) if lit.startswith("~") else assignment[lit] for lit in clause)
        for clause in clause_list
    )


def _collect_phrases(node, found: list[str]) -> list[str]:
    match node:
        case Atom(phrase):
            if phrase not in found:
                found.append(phrase)
        case Not(item):
            _collect_phrases(item, found)
        case And(items) | Or(items):
            for i in items:
                _collect_phrases(i, found)
        case Implies(a, b) | Iff(a, b):
            _collect_phrases(a, found)
            _collect_phrases(b, found)
    return found


def _random_formula(rng: random.Random, phrases):
    def clause_node():
        atom = Atom(rng.choice(phrases))
        return Not(atom) if rng.random() < 0.3 else atom

    def junction():
        roll = rng.random()
        if roll < 0.45:
            return clause_node()
        items = tuple(clause_node() for _ in range(rng.randint(2, 3)))
        return And(items) if roll < 0.72 else Or(items)

    roll = rng.random()
    if roll < 0.35:
        return junction()
    if roll < 0.75:
        return Implies(junction(), junction())
    return Iff(clause_node(), clause_node())


@pytest.mark.parametrize("negate_goal", [False, True])
def test_cnf_is_truth_table_equivalent_to_the_formula(negate_goal: bool) -> None:
    # The property that matters. CNF conversion must preserve the formula's value on EVERY
    # assignment -- equivalence, not just satisfiability -- because the student's proof and the
    # entailment verdict are both computed from these clauses.
    rng = random.Random(20261008)
    phrases = ["alpha", "bravo", "charlie", "delta", "echo"]
    literal_of = dict(zip(phrases, ("A", "~B", "C", "D", "~E"), strict=True)).get
    symbols = _symbols(literal_of, phrases)

    for _ in range(300):
        node = _random_formula(rng, phrases)
        produced = [
            canonical(c)
            for c in (goal_clauses if negate_goal else premise_clauses)(node, literal_of)
        ]
        used = _collect_phrases(node, [])
        local = sorted({literal_of(p).lstrip("~") for p in used})
        for bits in range(2 ** len(local)):
            assignment = {sym: bool(bits >> i & 1) for i, sym in enumerate(local)} | dict.fromkeys(
                symbols, False
            )
            expected = _eval_ast(node, assignment, literal_of)
            if negate_goal:
                expected = not expected
            assert _eval_clauses(produced, assignment) is expected, (
                f"{node!r} -> {produced} disagrees at {assignment}"
            )


def test_cnf_is_deterministic() -> None:
    rng = random.Random(7)
    phrases = ["alpha", "bravo", "charlie"]
    literal_of = dict(zip(phrases, ("A", "B", "C"), strict=True)).get
    for _ in range(50):
        node = _random_formula(rng, phrases)
        first = [canonical(c) for c in premise_clauses(node, literal_of)]
        assert first == [canonical(c) for c in premise_clauses(node, literal_of)]
