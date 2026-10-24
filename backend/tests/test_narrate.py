"""Contract tests for the M2 proof narration layer."""

from src.core.models import ClauseRec
from src.core.narrate import narrate


def test_narrate_mentions_every_step() -> None:
    clauses = (
        ClauseRec("c1", ("~A", "B"), "given", "s1"),
        ClauseRec("c2", ("A",), "given", "s2"),
        ClauseRec("c3", ("~B",), "goal"),
        ClauseRec("c4", ("B",), "derived"),
        ClauseRec("c5", (), "derived"),
    )

    explanation = "\n".join(narrate(clauses))

    for clause in clauses:
        assert clause.id in explanation
        for literal in clause.literals:
            assert literal in explanation
    assert "empty clause" in explanation


def test_narrate_distinguishes_given_goal_and_derived() -> None:
    # The module's whole purpose is letting the Explanation panel say where a clause came from --
    # a mutant that narrates "given" and "goal" clauses with "derived" wording must fail here.
    clauses = (
        ClauseRec("c1", ("A",), "given", "s1"),
        ClauseRec("c2", ("~A",), "goal"),
        ClauseRec("c3", (), "derived"),
    )

    explanation = "\n".join(narrate(clauses))

    assert "c1 is the given clause" in explanation
    assert "c2 is the negated conclusion" in explanation
    assert "c3 is derived" in explanation
