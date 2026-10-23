"""Contract tests for the M2 proof narration layer."""

from src.core.models import ClauseRec
from src.core.narrate import narrate


def test_narrate_mentions_every_step() -> None:
    clauses = (
        ClauseRec("c1", ("~A", "B"), "given", "s1"),
        ClauseRec("c2", ("A",), "given", "s2"),
        ClauseRec("c3", ("B",), "derived"),
        ClauseRec("c4", (), "derived"),
    )

    explanation = "\n".join(narrate(clauses))

    for clause in clauses:
        assert clause.id in explanation
        for literal in clause.literals:
            assert literal in explanation
    assert "empty clause" in explanation
