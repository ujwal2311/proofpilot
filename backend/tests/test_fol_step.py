"""Tests for core.fol_step -- validating a student's own FOL resolution step (HLD S18.16.2).

Written before the implementation. The contract's diagnosis order is the thing under test: each
error below is reached by a clause pair where EXACTLY that mistake is the right name for what the
student did, and the fallback is reached only when no more specific name applies.

WHY THIS MODULE IS CORRECTNESS-CRITICAL. A validator that accepts an unsound step teaches the
student that the step is sound. That is worse than refusing to validate at all, which is why
invariant I1 below ties legality to `resolve()` itself rather than to a second implementation of
the resolution rule that could drift away from it.
"""

import pytest
from src.core.fol_models import Constant, FunctionTerm, Predicate, Variable
from src.core.fol_resolve import resolve
from src.core.fol_step import (
    FolAnswerSyntaxError,
    FolStepError,
    check_fol_step,
    parse_clause_text,
    parse_literal_text,
)

x, y = Variable("x"), Variable("y")
socrates, alice, bob = Constant("socrates"), Constant("alice"), Constant("bob")


def human(t: object) -> Predicate:
    return Predicate("Human", (t,))  # type: ignore[arg-type]


def mortal(t: object) -> Predicate:
    return Predicate("Mortal", (t,))  # type: ignore[arg-type]


def wise(t: object) -> Predicate:
    return Predicate("Wise", (t,))  # type: ignore[arg-type]


# ------------------------------------------------------------------- I1: legal steps return None


def test_the_socrates_step_is_accepted() -> None:
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    assert check_fol_step(a, b, frozenset({(True, mortal(socrates))})) is None


def test_deriving_the_empty_clause_is_accepted() -> None:
    a = frozenset({(True, mortal(socrates))})
    b = frozenset({(False, mortal(socrates))})
    assert check_fol_step(a, b, frozenset()) is None


def test_every_resolvent_resolve_returns_is_accepted() -> None:
    """I1 stated directly: `check_fol_step` says yes to exactly what `resolve` produces."""
    # Two independent pivots, neither producing a tautology -- an earlier fixture here resolved
    # only into tautologies, which `resolve` filters, so the assertion below caught it as
    # vacuous rather than letting the test pass on an empty list.
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates)), (True, human(alice))})
    legal = [r for r, _mgu in resolve(a, b)]
    assert len(legal) == 2, "fixture must have legal resolvents or this passes vacuously"
    for resolvent in legal:
        assert check_fol_step(a, b, resolvent) is None


def test_clause_order_does_not_change_the_verdict() -> None:
    """I4: resolution is symmetric, so picking the clauses the other way round is the same step."""
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    typed = frozenset({(True, mortal(socrates))})
    assert check_fol_step(a, b, typed) == check_fol_step(b, a, typed)


# ------------------------------------------------------------- 1: nothing resolvable at all


def test_no_complementary_pair_is_named_as_such() -> None:
    a = frozenset({(True, human(socrates))})
    b = frozenset({(True, mortal(socrates))})  # same polarity, different predicate
    assert check_fol_step(a, b, frozenset()) is FolStepError.FOL_STEP_NOT_COMPLEMENTARY


def test_opposite_polarity_but_different_predicates_is_not_complementary() -> None:
    """Opposite polarity alone is not a resolvable pair -- there must be a predicate in common,
    or there is nothing a unifier could even be asked about."""
    a = frozenset({(True, human(socrates))})
    b = frozenset({(False, mortal(socrates))})
    assert check_fol_step(a, b, frozenset()) is FolStepError.FOL_STEP_NOT_COMPLEMENTARY


def test_resolving_against_the_empty_clause_is_not_complementary() -> None:
    a = frozenset({(True, human(socrates))})
    assert check_fol_step(a, frozenset(), frozenset()) is FolStepError.FOL_STEP_NOT_COMPLEMENTARY


# ------------------------------------------------------------------ 2: the pair will not unify


def test_matching_predicates_whose_arguments_clash_is_a_unifier_failure() -> None:
    a = frozenset({(True, human(socrates))})
    b = frozenset({(False, human(alice))})  # two different constants cannot unify
    assert check_fol_step(a, b, frozenset()) is FolStepError.FOL_STEP_NO_UNIFIER


def test_the_occurs_check_is_reported_as_a_unifier_failure_not_hidden() -> None:
    """x against f(x) fails the occurs check. That is a teachable fact about unification, so it
    is named the same way any other unification failure is -- never swallowed as "wrong"."""
    a = frozenset({(True, Predicate("P", (x,)))})
    b = frozenset({(False, Predicate("P", (FunctionTerm("f", (x,)),)))})
    assert check_fol_step(a, b, frozenset()) is FolStepError.FOL_STEP_NO_UNIFIER


# -------------------------------------------------------------- 3: two pairs cancelled at once


def test_cancelling_two_complementary_pairs_at_once_is_named() -> None:
    # Both Human and Wise are complementary across the two clauses. Resolution may cancel ONE
    # pair per step; cancelling both at once is unsound and is the classic mistake.
    a = frozenset({(True, human(socrates)), (True, wise(socrates)), (True, mortal(socrates))})
    b = frozenset({(False, human(socrates)), (False, wise(socrates))})
    assert check_fol_step(a, b, frozenset({(True, mortal(socrates))})) is (
        FolStepError.FOL_STEP_DOUBLE_RESOLVE
    )


# ---------------------------------------------- 4: the MGU was not applied to surviving literals


def test_substitution_applied_only_to_the_resolved_literals_is_named() -> None:
    """HLD S18.5's stated unsoundness. Resolving {¬Human(x), Mortal(x)} with {Human(socrates)}
    binds x to socrates, so the SURVIVING Mortal(x) must become Mortal(socrates). Leaving it as
    Mortal(x) is the mistake this code exists to name."""
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    assert check_fol_step(a, b, frozenset({(True, mortal(x))})) is (
        FolStepError.FOL_STEP_SUBST_INCOMPLETE
    )


def test_a_ground_step_can_never_be_substitution_incomplete() -> None:
    """Nothing was substituted, so that diagnosis cannot apply -- it falls through to the
    honest fallback instead of being forced onto the nearest-looking name."""
    a = frozenset({(False, human(socrates)), (True, mortal(socrates))})
    b = frozenset({(True, human(socrates))})
    verdict = check_fol_step(a, b, frozenset({(True, wise(socrates))}))
    assert verdict is FolStepError.FOL_STEP_WRONG_RESOLVENT


# ------------------------------------------------------------------------- 5: honest fallback


def test_an_unrelated_resolvent_is_the_fallback_not_a_guess() -> None:
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    assert check_fol_step(a, b, frozenset({(True, wise(bob))})) is (
        FolStepError.FOL_STEP_WRONG_RESOLVENT
    )


def test_dropping_a_surviving_literal_is_the_fallback() -> None:
    a = frozenset({(False, human(x)), (True, mortal(x)), (True, wise(x))})
    b = frozenset({(True, human(socrates))})
    # Mortal(socrates) alone drops Wise(socrates), which had to survive.
    assert check_fol_step(a, b, frozenset({(True, mortal(socrates))})) is (
        FolStepError.FOL_STEP_WRONG_RESOLVENT
    )


def test_a_tautological_resolvent_is_rejected() -> None:
    """`resolve` filters tautologies, so one is never legal -- I1 means this must be refused."""
    a = frozenset({(False, human(socrates)), (True, wise(socrates))})
    b = frozenset({(True, human(socrates)), (False, wise(socrates))})
    typed = frozenset({(True, wise(socrates)), (False, wise(socrates))})
    assert check_fol_step(a, b, typed) is not None


# --------------------------------------------------------------------------------- purity (I2)


def test_the_inputs_are_not_mutated() -> None:
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    before_a, before_b = set(a), set(b)
    check_fol_step(a, b, frozenset({(True, mortal(x))}))
    assert set(a) == before_a and set(b) == before_b


def test_repeated_calls_agree() -> None:
    a = frozenset({(False, human(x)), (True, mortal(x))})
    b = frozenset({(True, human(socrates))})
    typed = frozenset({(True, mortal(x))})
    assert check_fol_step(a, b, typed) == check_fol_step(a, b, typed)


# ---------------------------- parsing a student's typed answer (HLD S18.16, 2026-11-02) ----------
#
# Formal clause notation (¬Study(ravi) ∨ PassTheExam(ravi)), not English -- fol_english.py parses
# paragraphs, a different grammar entirely. Pure syntax ONLY: a raw term string is not yet a
# Variable or a Constant -- that needs each clause's own display naming (app.render), which
# core_fol does not own (HLD S18.14.2). The caller classifies each token; this module never does.

# --------------------------------------------------------------------------- accepted forms


def test_a_bare_zero_arity_predicate() -> None:
    assert parse_literal_text("Raining") == (False, "Raining", ())


def test_a_single_argument_predicate() -> None:
    assert parse_literal_text("Study(ravi)") == (False, "Study", ("ravi",))


def test_negation_with_the_unicode_symbol() -> None:
    assert parse_literal_text("¬Study(ravi)") == (True, "Study", ("ravi",))


def test_negation_with_the_ascii_alternative() -> None:
    assert parse_literal_text("~Study(ravi)") == (True, "Study", ("ravi",))


def test_a_multi_argument_predicate() -> None:
    assert parse_literal_text("Teaches(alice,bob)") == (False, "Teaches", ("alice", "bob"))


def test_whitespace_is_tolerated_everywhere() -> None:
    assert parse_literal_text(" ¬ Teaches ( alice , bob ) ") == (True, "Teaches", ("alice", "bob"))


def test_predicate_name_case_is_preserved_not_folded() -> None:
    """Case is cosmetic to the parser but not normalized away -- `resolve()` matches predicate
    names exactly, so folding case here would let a typo silently 'succeed' syntactically while
    failing to match anything semantically, which is a worse failure mode than just parsing it
    as typed and letting check_fol_step say NOT_COMPLEMENTARY honestly."""
    assert parse_literal_text("PassTheExam(ravi)")[1] == "PassTheExam"


def test_a_variable_shaped_term_parses_the_same_as_any_other_term() -> None:
    """At this layer "x" is just a raw string -- nothing here decides it is a variable."""
    assert parse_literal_text("Study(x)") == (False, "Study", ("x",))


def test_clause_splits_on_or_into_each_literal() -> None:
    assert parse_clause_text("¬Study(ravi) ∨ PassTheExam(ravi)") == (
        (True, "Study", ("ravi",)),
        (False, "PassTheExam", ("ravi",)),
    )


def test_clause_of_one_literal_is_a_one_tuple() -> None:
    assert parse_clause_text("Student(ravi)") == ((False, "Student", ("ravi",)),)


def test_blank_input_is_the_empty_clause() -> None:
    assert parse_clause_text("") == ()
    assert parse_clause_text("   ") == ()


# ------------------------------------------------------------------------------- rejections


def test_an_empty_literal_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError) as excinfo:
        parse_literal_text("")
    assert excinfo.value.text == ""


def test_unbalanced_parens_missing_close_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("Study(ravi")


def test_unbalanced_parens_missing_open_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("Studyravi)")


def test_double_negation_is_rejected_not_silently_collapsed() -> None:
    """Same discipline as core.logic.normalize_literal: collapsing ~~P would be a guess about
    what the student meant."""
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("¬¬Study(ravi)")


def test_a_malformed_predicate_name_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("1Study(ravi)")


def test_a_malformed_term_token_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("Study(1ravi)")


def test_a_trailing_comma_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("Teaches(alice,)")


def test_an_empty_term_between_commas_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("Teaches(alice,,bob)")


def test_garbage_input_is_rejected() -> None:
    with pytest.raises(FolAnswerSyntaxError):
        parse_literal_text("###not a literal###")


def test_the_offending_text_is_attached_to_the_error() -> None:
    with pytest.raises(FolAnswerSyntaxError) as excinfo:
        parse_literal_text("Study(1ravi)")
    assert excinfo.value.text == "Study(1ravi)"


def test_a_malformed_literal_inside_an_or_clause_is_rejected() -> None:
    """One bad literal fails the whole clause -- never guess which half the student meant."""
    with pytest.raises(FolAnswerSyntaxError):
        parse_clause_text("Study(ravi) ∨ 1Bad(x)")
