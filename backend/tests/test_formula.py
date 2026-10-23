"""Contract tests for the M2 typed propositional-formula parser.

The parser accepts proposition symbols, parentheses, and the five documented
connectives in ASCII or Unicode. It must reject malformed input by name rather
than interpreting an incomplete formula.
"""

import pytest
from src.core.formula import FormulaError, evaluate, parse


@pytest.mark.parametrize(
    ("text", "row", "expected"),
    [
        ("A", {"A": True}, True),
        ("~A", {"A": True}, False),
        ("A & B", {"A": True, "B": False}, False),
        ("A | B", {"A": True, "B": False}, True),
        ("A -> B", {"A": True, "B": False}, False),
        ("A <-> B", {"A": True, "B": True}, True),
        ("¬A ∨ (B ∧ C)", {"A": True, "B": True, "C": False}, False),
    ],
)
def test_parse_accepts_the_five_connectives_in_ascii_or_unicode(text, row, expected) -> None:
    assert evaluate(parse(text), row) is expected


@pytest.mark.parametrize("text", ("", "A ->", "(A | B", "A B", "A + B", "AA"))
def test_parse_refuses_a_malformed_or_unsupported_formula(text) -> None:
    with pytest.raises(FormulaError):
        parse(text)


def test_missing_symbol_in_an_assignment_is_a_named_refusal() -> None:
    with pytest.raises(FormulaError, match="no value"):
        evaluate(parse("A & B"), {"A": True})
