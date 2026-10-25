"""Tests for app.render's clause-to-English rendering.

Deliberately fresh vocabulary -- printers and toner, not rain or buses -- to prove the function
generalizes over any clause/fact pair rather than matching content used to build it.
"""

from src.app.render import clause_english, clause_english_map
from src.core.models import ClauseRec, Fact

FACTS = (
    Fact("A", (("p1", "the printer is low on toner"),)),
    Fact("B", (("p2", "the job is queued"),)),
    # A merged fact: TWO phrases absorbed into one symbol. Only the first should ever render.
    Fact("C", (("p3", "the tray is empty"), ("p4", "paper has run out"))),
)


def test_single_positive_literal() -> None:
    clause = ClauseRec("c1", ("A",), "given", "s1")
    assert clause_english(clause, FACTS) == "the printer is low on toner"


def test_negated_literal_gets_a_not_prefix() -> None:
    clause = ClauseRec("c1", ("~B",), "given", "s1")
    assert clause_english(clause, FACTS) == "not the job is queued"


def test_multiple_literals_joined_with_or() -> None:
    clause = ClauseRec("c1", ("A", "~B", "C"), "derived", None)
    assert clause_english(clause, FACTS) == (
        "the printer is low on toner or not the job is queued or the tray is empty"
    )


def test_empty_clause_is_a_contradiction() -> None:
    clause = ClauseRec("c7", (), "derived", None)
    assert clause_english(clause, FACTS) == "a contradiction"


def test_merged_fact_uses_only_its_first_phrase() -> None:
    # C absorbed two phrases ("the tray is empty" / "paper has run out"); the second must never
    # appear in a rendered clause, or a sentence the student never wrote would show up here.
    clause = ClauseRec("c1", ("C",), "given", "s3")
    text = clause_english(clause, FACTS)
    assert text == "the tray is empty"
    assert "paper has run out" not in text


def test_clause_english_map_keys_every_clause_by_id() -> None:
    clauses = (
        ClauseRec("c1", ("A", "~B"), "given", "s1"),
        ClauseRec("c2", (), "derived", None),
    )
    state = _FakeState(clauses, FACTS)
    assert clause_english_map(state) == {
        "c1": "the printer is low on toner or not the job is queued",
        "c2": "a contradiction",
    }


class _FakeState:
    """`clause_english_map` only ever reads `.clauses` and `.facts` off its argument -- a real
    `State` carries a dozen other fields that are irrelevant here and expensive to construct."""

    def __init__(self, clauses, facts) -> None:
        self.clauses = clauses
        self.facts = facts
