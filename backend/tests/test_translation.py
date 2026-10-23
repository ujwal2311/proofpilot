"""Contract tests for M2 translation equivalence and its fixed diagnoses."""

from src.core.translation import check

LABELS = {"A": "it rains", "B": "we get wet"}


def test_contrapositive_accepted_with_note() -> None:
    result = check("A -> B", "~B -> ~A", LABELS)

    assert result.code == "CORRECT_CONTRAPOSITIVE"
    assert result.counterexample is None


def test_translation_converse_detected() -> None:
    result = check("A -> B", "B -> A", LABELS)

    assert result.code == "CONVERSE"
    assert result.counterexample is not None


def test_translation_missing_negation_detected() -> None:
    result = check("~A -> B", "A -> B", LABELS)

    assert result.code == "MISSING_NEGATION"


def test_translation_and_or_swap_detected() -> None:
    result = check("A & B", "A | B", LABELS)

    assert result.code == "AND_OR_SWAP"


def test_translation_counterexample_differs_in_truth_value() -> None:
    result = check("A -> B", "B -> A", LABELS)

    assert result.counterexample is not None
    row = dict(result.counterexample)
    assert row["it rains"] is True
    assert row["we get wet"] is False
