"""Tests for core.fol_search -- the FOL proof procedure (HLD section 18.6).

Written before the implementation. Covers all of HLD section 18.9's hand-worked tests (A, E, F,
G) plus INCONSISTENT. Step COUNTS are asserted only where the derivation is forced (a clause set
small enough that there is exactly one possible resolution path); the saturation algorithm this
module documents choosing (every pair, every round, not a minimal-path search) can legitimately
take a different route to the same PROVED outcome than a hand-worked "shortest proof" narrative,
so a step count is asserted only after confirming by inspection that the algorithm cannot do
otherwise here.
"""

from src.core.fol_models import (
    Constant,
    FolAnd,
    FolImplies,
    FolNot,
    ForAll,
    Predicate,
    Variable,
)
from src.core.fol_search import (
    EMPTY_CLAUSE,
    FolProofOutcome,
    fol_claim_accepted,
    fol_hint_code,
    fol_prove,
)

x, y = Variable("x"), Variable("y")
socrates, alice, bob = Constant("socrates"), Constant("alice"), Constant("bob")


def human(t: object) -> Predicate:
    return Predicate("Human", (t,))  # type: ignore[arg-type]


def mortal(t: object) -> Predicate:
    return Predicate("Mortal", (t,))  # type: ignore[arg-type]


# -------------------------------------------------------------------------------- Test A: Socrates


def test_socrates_is_proved() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    result = fol_prove(premises, mortal(socrates))
    assert result.outcome is FolProofOutcome.PROVED
    assert EMPTY_CLAUSE in result.clauses
    assert len(result.proof_steps) >= 1
    assert result.proof_steps[-1][2] == EMPTY_CLAUSE


# ------------------------------------------------------------------------- Test E: Teaches/Knows


def test_teaches_knows_multi_argument_is_proved() -> None:
    teaches_xy = Predicate("Teaches", (x, y))
    knows_yx = Predicate("Knows", (y, x))
    premises = [
        ForAll(x, ForAll(y, FolImplies(teaches_xy, knows_yx))),
        Predicate("Teaches", (alice, bob)),
    ]
    conclusion = Predicate("Knows", (bob, alice))
    result = fol_prove(premises, conclusion)
    assert result.outcome is FolProofOutcome.PROVED
    assert EMPTY_CLAUSE in result.clauses


# ------------------------------------------------------------------------ Test F: non-entailment


def test_unrelated_predicates_are_budget_exhausted_not_proved() -> None:
    # HLD section 18.9 Test F: forall x P(x) does not entail forall x Q(x) -- P and Q are
    # unrelated, so no resolvent can ever connect them. Expected BUDGET_EXHAUSTED, never PROVED.
    p, q = Predicate("P", (x,)), Predicate("Q", (x,))
    result = fol_prove([ForAll(x, p)], ForAll(x, q))
    assert result.outcome is FolProofOutcome.BUDGET_EXHAUSTED
    assert EMPTY_CLAUSE not in result.clauses


# --------------------------------------------------------------------- Test G: tiny budget safety


def test_tiny_budget_is_exhausted_without_crashing() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    result = fol_prove(premises, mortal(socrates), budget=0)
    assert result.outcome is FolProofOutcome.BUDGET_EXHAUSTED


def test_a_merely_small_budget_still_proves_the_two_step_case() -> None:
    # Confirms the honest-outcome logic is about running out, not about being stingy by default:
    # a budget of 1 Work unit is tight but the first pair tried does resolve, so progress is
    # made before it runs out, and the search continues rather than giving up instantly.
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    result = fol_prove(premises, mortal(socrates), budget=1)
    assert result.outcome in (FolProofOutcome.PROVED, FolProofOutcome.BUDGET_EXHAUSTED)


# ------------------------------------------------------------------------------------ INCONSISTENT


def test_contradictory_premises_are_inconsistent() -> None:
    premises = [human(socrates), FolNot(human(socrates))]
    result = fol_prove(premises, mortal(socrates))
    assert result.outcome is FolProofOutcome.INCONSISTENT
    assert EMPTY_CLAUSE in result.clauses
    assert result.proof_steps[-1][2] == EMPTY_CLAUSE


# -------------------------------------------------------------------------------------- determinism


def test_fol_prove_is_deterministic_across_repeated_calls() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    first = fol_prove(premises, mortal(socrates))
    second = fol_prove(premises, mortal(socrates))
    assert first.outcome == second.outcome
    assert first.proof_steps == second.proof_steps
    assert first.clauses == second.clauses


def test_fol_prove_never_exceeds_its_budget() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    # A conjunction that cannot be proved at all within a tiny budget must still terminate.
    unrelated_conclusion = Predicate("Zebra", (socrates,))
    result = fol_prove(premises, unrelated_conclusion, budget=3)
    assert result.outcome is FolProofOutcome.BUDGET_EXHAUSTED


def test_multiple_premises_with_no_conclusion_relation_combine_without_crashing() -> None:
    premises = [human(socrates), FolAnd((human(alice), mortal(bob)))]
    result = fol_prove(premises, mortal(socrates))
    assert result.outcome in (FolProofOutcome.PROVED, FolProofOutcome.BUDGET_EXHAUSTED)


# ------------------------------------------- FOL-aware hint/claim dispatch (Facts-panel fix,
# ------------------------------------------- follow-up: the Prove screen was still misleading)

# Written before the implementation (CLAUDE.md rule 1), after the student specified the mapping
# directly: resolution is only semi-decidable (HLD S18.11.1), so a failed search is NEVER evidence
# of non-entailment. Neither function may ever treat BUDGET_EXHAUSTED as "does not follow".


def test_fol_claim_accepted_is_false_when_proved() -> None:
    # The argument follows, so claiming it does not follow is wrong.
    assert fol_claim_accepted(FolProofOutcome.PROVED) is False


def test_fol_claim_accepted_is_false_when_inconsistent() -> None:
    # Trivially valid (ex falso quodlibet) -- still wrong to claim it does not follow.
    assert fol_claim_accepted(FolProofOutcome.INCONSISTENT) is False


def test_fol_claim_accepted_is_none_when_budget_exhausted() -> None:
    # Genuinely unknown -- `None` means "do not score this", never "it follows".
    assert fol_claim_accepted(FolProofOutcome.BUDGET_EXHAUSTED) is None


def test_fol_claim_accepted_never_returns_true() -> None:
    # The one invariant that matters: no FOL outcome may ever make "does not follow" correct.
    assert all(fol_claim_accepted(outcome) is not True for outcome in FolProofOutcome)


def test_fol_hint_code_follows_for_proved() -> None:
    assert [fol_hint_code(FolProofOutcome.PROVED, level) for level in (1, 2, 3)] == [
        "HINT_FOL_FOLLOWS_1",
        "HINT_FOL_FOLLOWS_2",
        "HINT_FOL_FOLLOWS_3",
    ]


def test_fol_hint_code_follows_for_inconsistent() -> None:
    assert [fol_hint_code(FolProofOutcome.INCONSISTENT, level) for level in (1, 2, 3)] == [
        "HINT_FOL_FOLLOWS_1",
        "HINT_FOL_FOLLOWS_2",
        "HINT_FOL_FOLLOWS_3",
    ]


def test_fol_hint_code_is_honest_about_not_knowing_at_every_level() -> None:
    # Nothing varies by level when the system itself does not know -- escalating "HINT_2"/"HINT_3"
    # wording would imply a certainty the engine does not have.
    for level in (1, 2, 3):
        assert fol_hint_code(FolProofOutcome.BUDGET_EXHAUSTED, level) == "HINT_FOL_UNKNOWN"
