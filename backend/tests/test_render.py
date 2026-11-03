"""Tests for app.render's clause-to-English rendering.

Deliberately fresh vocabulary -- printers and toner, not rain or buses -- to prove the function
generalizes over any clause/fact pair rather than matching content used to build it.
"""

from src.app.render import Renderer, clause_english, clause_english_map
from src.core.logic import Code, Diagnosis
from src.core.models import ClauseRec, Fact, SentenceRec

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


# ------------------------- sentence_errors: the web UI's missing error prose (2026-11-02) -------
#
# Renderer.error() already renders a code into its messages.yaml prose, rephrasing hint included
# -- but it was called ONLY from the CLI. The web UI showed the bare code string for every
# per-sentence refusal, propositional or FOL. This reuses error() as-is; no new wording.

ERROR_TEXT = Renderer(
    text={
        "error": {
            "QUANTIFIER_UNSUPPORTED": (
                'words like "all" are beyond this system. Rewrite about one specific case.'
            ),
            "UNPARSEABLE": "I cannot read that sentence.",
        }
    }
)


def test_sentence_errors_renders_the_refused_sentences_message() -> None:
    sentences = (
        SentenceRec("s1", "All engineers solve problems", "error", "QUANTIFIER_UNSUPPORTED"),
        SentenceRec("s2", "Aisha is an engineer", "ok", None),
    )
    assert ERROR_TEXT.sentence_errors(sentences) == {
        "s1": 'words like "all" are beyond this system. Rewrite about one specific case.'
    }


def test_sentence_errors_is_empty_when_nothing_was_refused() -> None:
    sentences = (SentenceRec("s1", "Aisha is an engineer", "ok", None),)
    assert ERROR_TEXT.sentence_errors(sentences) == {}


def test_sentence_errors_covers_more_than_one_refused_sentence() -> None:
    sentences = (
        SentenceRec("s1", "All engineers solve problems", "error", "QUANTIFIER_UNSUPPORTED"),
        SentenceRec("s2", "garble garble", "error", "UNPARSEABLE"),
        SentenceRec("s3", "Aisha is an engineer", "ok", None),
    )
    errors = ERROR_TEXT.sentence_errors(sentences)
    assert set(errors) == {"s1", "s2"}
    assert errors["s2"] == "I cannot read that sentence."


# ----------------------- step(): VALID dropped its own lead-in text (found live, 2026-11-03) ----
#
# `step()` rendered a productive/unproductive/unknown VALID step as JUST the `productivity.*`
# text -- "that shortens the proof." on its own, with `step.VALID` ("valid.") defined in
# messages.yaml but never read by any code path for this case. A student saw a feedback banner
# whose rendered sentence read "VALID that shortens the proof." with no verb.

STEP_TEXT = Renderer(
    text={
        "step": {"VALID": "valid."},
        "productivity": {
            # Capitalized at the source: each is concatenated as a SECOND sentence after
            # `step.VALID`, so `.feedback::first-letter` (which only reaches the message's own
            # first letter) can never capitalize these -- found live, 2026-11-03.
            "productive": "That shortens the proof.",
            "unproductive": "Legal, but no closer to a refutation.",
            "unknown": "Legal. (the search ran out of its budget, so I cannot say if it helps.)",
        },
    }
)


def test_step_valid_productive_includes_its_own_lead_in() -> None:
    found = Diagnosis(Code.VALID)
    assert STEP_TEXT.step(found, productive=True) == "valid. That shortens the proof."


def test_step_valid_unproductive_includes_its_own_lead_in() -> None:
    found = Diagnosis(Code.VALID)
    assert STEP_TEXT.step(found, productive=False) == "valid. Legal, but no closer to a refutation."


def test_step_valid_unknown_includes_its_own_lead_in() -> None:
    found = Diagnosis(Code.VALID)
    assert STEP_TEXT.step(found, productive=None) == (
        "valid. Legal. (the search ran out of its budget, so I cannot say if it helps.)"
    )
