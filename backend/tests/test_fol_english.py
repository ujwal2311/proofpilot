"""Tests for core.fol_english -- the controlled FOL grammar (HLD section 18.2).

Written before the implementation. Every worked example in HLD section 18.2.2 is reproduced
exactly, plus the named-error table (section 18.2.4) and the reserved-word guard this
implementation adds (see the module docstring's limitations list) to stop a malformed sentence
like "Every human likes every dog" from silently becoming one bogus CamelCased predicate.
"""

import pytest
from src.core.fol_english import FolErrorCode, FolParseError, detect_mode, is_fol_formula, parse
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolImplies,
    FolNot,
    ForAll,
    Predicate,
    Variable,
)

v = Variable("x")


# ----------------------------------------------------------------------------------- "every"/"no"


def test_every_x_is_a_y() -> None:
    assert parse("Every human is mortal") == ForAll(
        v, FolImplies(Predicate("Human", (v,)), Predicate("Mortal", (v,)))
    )


def test_every_x_is_not_a_y() -> None:
    assert parse("Every prime is not even") == ForAll(
        v, FolImplies(Predicate("Prime", (v,)), FolNot(Predicate("Even", (v,))))
    )


def test_no_x_is_a_y() -> None:
    assert parse("No cat is a dog") == ForAll(
        v, FolImplies(Predicate("Cat", (v,)), FolNot(Predicate("Dog", (v,))))
    )


def test_no_x_is_not_a_y_is_refused_as_an_undocumented_variant() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("No cat is not a dog")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


# ---------------------------------------------------------------------------------------- "some"


def test_some_x_is_a_y_with_no_copula_at_all() -> None:
    # HLD section 18.2.2's own example has no "is": the predicate slot is read as whatever
    # remains after the subject, "is" present or not.
    assert parse("Some student studies") == Exists(
        v, FolAnd((Predicate("Student", (v,)), Predicate("Studies", (v,))))
    )


def test_some_x_is_not_a_y_is_refused_as_an_undocumented_variant() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Some student is not lazy")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


# ----------------------------------------------------------------------------------- "all...that"


def test_all_x_that_y_are_z_with_no_copula() -> None:
    # HLD section 18.2.2's own example, "All students that study pass", has no "are" either.
    assert parse("All students that study pass") == ForAll(
        v,
        FolImplies(
            FolAnd((Predicate("Students", (v,)), Predicate("Study", (v,)))), Predicate("Pass", (v,))
        ),
    )


def test_all_x_that_y_are_z_with_explicit_copula() -> None:
    result = parse("All birds that fly are migratory")
    expected = ForAll(
        v,
        FolImplies(
            FolAnd((Predicate("Birds", (v,)), Predicate("Fly", (v,)))),
            Predicate("Migratory", (v,)),
        ),
    )
    assert result == expected


def test_all_without_that_is_refused() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("All students pass")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


# -------------------------------------------------------------------------------- ground patterns


def test_name_rs_name() -> None:
    assert parse("Alice likes Bob") == Predicate("Likes", (Constant("alice"), Constant("bob")))


def test_name_rs_name_and_name() -> None:
    result = parse("Alice likes Bob and Carol")
    likes_ab = Predicate("Likes", (Constant("alice"), Constant("bob")))
    likes_ac = Predicate("Likes", (Constant("alice"), Constant("carol")))
    assert result == FolAnd((likes_ab, likes_ac))


def test_name_is_a_y() -> None:
    assert parse("Socrates is a human") == Predicate("Human", (Constant("socrates"),))


def test_name_is_not_a_y() -> None:
    assert parse("Tweety is not a penguin") == FolNot(Predicate("Penguin", (Constant("tweety"),)))


# ----------------------------------------------------------------------------------- wh-patterns


def test_if_x_is_a_y_then_x_is_a_z() -> None:
    result = parse("If x is a bird then x is a flyer")
    expected = ForAll(v, FolImplies(Predicate("Bird", (v,)), Predicate("Flyer", (v,))))
    assert result == expected


def test_if_name_rs_name_then_name_rs_name() -> None:
    result = parse("If Alice teaches Bob then Bob knows Alice")
    teaches = Predicate("Teaches", (Constant("alice"), Constant("bob")))
    knows = Predicate("Knows", (Constant("bob"), Constant("alice")))
    assert result == FolImplies(teaches, knows)


def test_if_with_mismatched_subjects_is_refused() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("If x is a bird then y is a flyer")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


def test_if_without_then_is_refused() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("If x is a bird x is a flyer")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


# ---------------------------------------------------------------------------------- named errors


def test_unknown_pattern_for_unrecognisable_input() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Colorless green ideas sleep furiously today somehow")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


def test_nested_quantifier_in_ground_is_refused_specifically() -> None:
    # The gap this implementation closes explicitly: without the reserved-word guard, "likes
    # every dog" would silently CamelCase into one bogus predicate instead of being refused.
    with pytest.raises(FolParseError) as excinfo:
        parse("Every human likes every dog")
    assert excinfo.value.code is FolErrorCode.FOL_NESTED_QUANTIFIER_IN_GROUND


def test_nested_quantifier_in_a_ground_ambiguous_relation_slot() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Alice likes every dog")
    assert excinfo.value.code is FolErrorCode.FOL_NESTED_QUANTIFIER_IN_GROUND


def test_equality_is_refused_by_name() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Alice equals Bob")
    assert excinfo.value.code is FolErrorCode.FOL_UNSUPPORTED_ARITY


def test_is_the_same_as_is_refused_by_name() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Alice is the same as Bob")
    assert excinfo.value.code is FolErrorCode.FOL_UNSUPPORTED_ARITY


def test_sentence_too_long_is_refused() -> None:
    long_sentence = "every " + " ".join(f"word{i}" for i in range(40))
    with pytest.raises(FolParseError) as excinfo:
        parse(long_sentence)
    assert excinfo.value.code is FolErrorCode.FOL_SENTENCE_TOO_LONG


def test_ambiguous_individual_across_sentences_in_one_registry() -> None:
    registry: dict = {}
    parse("Alice likes Bob", registry)
    with pytest.raises(FolParseError) as excinfo:
        parse("Every alice is nice", registry)
    assert excinfo.value.code is FolErrorCode.FOL_AMBIGUOUS_INDIVIDUAL


def test_unsupported_arity_across_sentences_in_one_registry() -> None:
    registry: dict = {}
    parse("Alice likes Bob", registry)  # "likes" used with arity 2
    with pytest.raises(FolParseError) as excinfo:
        parse("Carol is a likes", registry)  # "likes" now used with arity 1
    assert excinfo.value.code is FolErrorCode.FOL_UNSUPPORTED_ARITY


def test_a_fresh_registry_per_call_does_not_cross_check() -> None:
    # No registry passed -> each call gets its own fresh one, so the same word in two
    # independent calls cannot conflict with itself (there is nothing else for it to conflict
    # with -- see parse()'s own docstring).
    parse("Alice likes Bob")
    parse("Every alice is nice")  # would conflict if sharing a registry; does not here


# -------------------------------------------------------------------------- predicate normalisation


def test_multi_word_relation_is_camel_cased() -> None:
    assert parse("Alice admires Bob") == Predicate("Admires", (Constant("alice"), Constant("bob")))


def test_individual_names_are_lowercased() -> None:
    result = parse("Socrates is a human")
    (arg,) = result.args
    assert arg == Constant("socrates")


# -------------------------------------------------------------------------------- mode detection


def test_is_fol_formula_true_for_a_quantifier() -> None:
    assert is_fol_formula(parse("Every human is mortal")) is True


def test_is_fol_formula_false_for_a_ground_unary_predicate() -> None:
    # A ground fact with no quantifier is not a reliable FOL signal (see is_fol_formula's own
    # docstring): "Socrates is a human" and an ordinary propositional sentence are equally
    # plausible readings of the same ground-predicate shape, without a quantifier to disambiguate.
    assert is_fol_formula(parse("Socrates is a human")) is False


def test_is_fol_formula_false_for_a_ground_binary_relation() -> None:
    # "Alice likes Bob" parses the identical way "We get wet" does (NAME verb NAME) -- neither
    # can be told apart from the other without guessing from capitalization, which this grammar
    # deliberately never does (section 18.2).
    assert is_fol_formula(parse("Alice likes Bob")) is False


def test_is_fol_formula_false_for_a_zero_arity_predicate() -> None:
    assert is_fol_formula(Predicate("Raining", ())) is False


def test_is_fol_formula_true_for_a_quantifier_nested_under_connectives() -> None:
    nested = FolAnd((Predicate("P", ()), ForAll(Variable("x"), Predicate("Q", (Variable("x"),)))))
    assert is_fol_formula(nested) is True


def test_detect_mode_is_fol_if_any_sentence_has_a_quantifier() -> None:
    assert detect_mode(["It rains.", "Every human is mortal."]) == "fol"


def test_detect_mode_is_prop_for_ground_relational_sentences_with_no_quantifier() -> None:
    # The case Phase 8 found during implementation: "We get wet" parses as the equally valid
    # Get(we, wet), so an arity-based signal would have flagged this paragraph "fol" too.
    assert detect_mode(["It rains.", "We get wet."]) == "prop"


def test_detect_mode_is_prop_for_an_ordinary_ground_fact_paragraph() -> None:
    assert detect_mode(["Alice likes Bob.", "Socrates is a human."]) == "prop"


def test_detect_mode_prop_for_a_sentence_that_fails_to_parse_at_all() -> None:
    # A parse failure is core.english's problem to refuse, not a FOL signal (module docstring).
    assert detect_mode(["Colorless green ideas sleep furiously today somehow."]) == "prop"
