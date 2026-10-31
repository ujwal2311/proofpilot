"""FOL sprint Phase 10: pipeline-level integration, English text through to a verdict.

Re-scoped at the Phase 8 gate (HLD section 18.12's note): the original "full integration tests"
meant through State/the API, which Phase 8b (not yet scheduled) has not wired up. This file
instead proves the engine built in Phases 1-7 works end to end from REAL ENGLISH TEXT --
`fol_english.parse()` -> `fol_cnf.to_fol_clauses()` (inside `fol_prove`) -> `fol_search.fol_prove()`
-- which Phase 7's own tests did not cover: those built `FolFormula` trees by hand.

One registry is shared across every sentence of one "paragraph", exactly as a real caller would
(HLD section 18.2's own cross-sentence contract), so a mistake in one sentence that conflicts
with another's use of the same word would be caught here too, not just in isolation.
"""

import pytest
from src.core.fol_english import FolErrorCode, FolParseError, Registry, parse
from src.core.fol_search import FolProofOutcome, fol_prove


def _prove(premises: list[str], conclusion: str, budget: int | None = None):
    registry: Registry = {}
    parsed_premises = [parse(sentence, registry) for sentence in premises]
    parsed_conclusion = parse(conclusion, registry)
    return fol_prove(parsed_premises, parsed_conclusion, budget)


# -------------------------------------------------------------------------------- Socrates, by text


def test_socrates_proved_end_to_end_from_text() -> None:
    result = _prove(["Every human is mortal", "Socrates is a human"], "Socrates is mortal")
    assert result.outcome is FolProofOutcome.PROVED


def test_socrates_is_deterministic_parsed_fresh_each_time() -> None:
    first = _prove(["Every human is mortal", "Socrates is a human"], "Socrates is mortal")
    second = _prove(["Every human is mortal", "Socrates is a human"], "Socrates is mortal")
    assert first.outcome == second.outcome
    assert first.proof_steps == second.proof_steps


# ----------------------------------------------------------------- unrelated predicates, by text


def test_unrelated_quantified_predicates_are_budget_exhausted_not_proved() -> None:
    # "Every bird flies" says nothing about fish; the pipeline-level analogue of HLD section
    # 18.9 Test F, parsed from text instead of built by hand.
    result = _prove(["Every bird flies"], "Every fish flies")
    assert result.outcome is FolProofOutcome.BUDGET_EXHAUSTED


def test_a_tiny_budget_is_exhausted_without_crashing_from_text() -> None:
    premises = ["Every human is mortal", "Socrates is a human"]
    result = _prove(premises, "Socrates is mortal", budget=0)
    assert result.outcome is FolProofOutcome.BUDGET_EXHAUSTED


# -------------------------------------------------------------------------- inconsistent, by text


def test_contradictory_ground_facts_are_inconsistent_from_text() -> None:
    result = _prove(["Socrates is a human", "Socrates is not a human"], "Socrates is mortal")
    assert result.outcome is FolProofOutcome.INCONSISTENT


# ------------------------------------------------------------------- a second worked case, by text


def test_a_second_unrelated_vocabulary_proves_the_same_shape() -> None:
    # A second worked case in different vocabulary, to catch a fix that happened to special-case
    # "human"/"mortal"/"socrates" rather than the pipeline generally (CLAUDE.md principle 1).
    result = _prove(["Every student is honest", "Alice is a student"], "Alice is honest")
    assert result.outcome is FolProofOutcome.PROVED


def test_multiply_quantified_binary_relations_are_out_of_scope() -> None:
    # Documents why Teaches/Knows (HLD section 18.9 Test E) stays a hand-built-formula test
    # (test_fol_search.py), not a text-parsed one here: the grammar cannot express
    # "for all x, for all y, if x teaches y then y knows x" at all.
    with pytest.raises(FolParseError) as excinfo:
        parse("Every teacher teaches every student")
    assert excinfo.value.code is FolErrorCode.FOL_NESTED_QUANTIFIER_IN_GROUND
