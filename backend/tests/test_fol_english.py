"""Tests for core.fol_english -- the controlled FOL grammar (HLD section 18.2).

Written before the implementation. Every worked example in HLD section 18.2.2 is reproduced
exactly, plus the named-error table (section 18.2.4) and the reserved-word guard this
implementation adds (see the module docstring's limitations list) to stop a malformed sentence
like "Every human likes every dog" from silently becoming one bogus CamelCased predicate.
"""

import pytest
from src.core.fol_english import (
    FolErrorCode,
    FolParseError,
    detect_mode,
    is_fol_formula,
    is_fol_sentence,
    parse,
    render,
)
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolIff,
    FolImplies,
    FolNot,
    FolOr,
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
        v, FolAnd((Predicate("Student", (v,)), Predicate("Study", (v,))))
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
            FolAnd((Predicate("Student", (v,)), Predicate("Study", (v,)))), Predicate("Pass", (v,))
        ),
    )


def test_all_x_that_y_are_z_with_explicit_copula() -> None:
    result = parse("All birds that fly are migratory")
    expected = ForAll(
        v,
        FolImplies(
            FolAnd((Predicate("Bird", (v,)), Predicate("Fly", (v,)))),
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
    assert parse("Alice likes Bob") == Predicate("Like", (Constant("alice"), Constant("bob")))


def test_name_rs_name_and_name() -> None:
    result = parse("Alice likes Bob and Carol")
    likes_ab = Predicate("Like", (Constant("alice"), Constant("bob")))
    likes_ac = Predicate("Like", (Constant("alice"), Constant("carol")))
    assert result == FolAnd((likes_ab, likes_ac))


def test_name_is_a_y() -> None:
    assert parse("Socrates is a human") == Predicate("Human", (Constant("socrates"),))


def test_name_is_not_a_y() -> None:
    assert parse("Tweety is not a penguin") == FolNot(Predicate("Penguin", (Constant("tweety"),)))


# ---------------- bare intransitive ground predicate
# (2026-11-02, student-authorized grammar extension, exact scope)


def test_name_bare_verb_is_a_unary_predicate() -> None:
    # "NAME VERBs" with no "is" and no object -- same shape as "NAME is a Y", just without the
    # copula. Needed for paragraphs like "Ravi studies" (CAT-2 worked example, 2026-11-02).
    assert parse("Ravi studies") == Predicate("Study", (Constant("ravi"),))


def test_name_bare_verb_negation_stays_out_of_scope() -> None:
    # "not" is a reserved structural word (section 18.2's own guard) -- "Ravi does not study" is
    # refused rather than silently read as a two-argument relation to a constant named "not".
    # Explicitly out of scope: the authorization was for the positive bare-verb form only.
    with pytest.raises(FolParseError) as excinfo:
        parse("Ravi does not study")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


# ------------------------------------------------------------ ground disjunction (2026-11-02, same
# ------------------------------------------------------------ student-authorized extension)


def test_ground_or_between_two_ground_sentences() -> None:
    result = parse("Ravi studies or Ravi is lucky")
    assert result == FolOr(
        (
            Predicate("Study", (Constant("ravi"),)),
            Predicate("Lucky", (Constant("ravi"),)),
        )
    )


def test_ground_or_composes_with_the_existing_and_pattern_on_either_side() -> None:
    # "A and B" on the left of "or" still parses via the existing relational-and pattern --
    # the "or" split is a thin wrapper, not a second grammar.
    result = parse("Alice likes Bob and Carol or Dave is happy")
    likes = FolAnd(
        (
            Predicate("Like", (Constant("alice"), Constant("bob"))),
            Predicate("Like", (Constant("alice"), Constant("carol"))),
        )
    )
    assert result == FolOr((likes, Predicate("Happy", (Constant("dave"),))))


def test_ground_or_twice_is_refused_as_ambiguous() -> None:
    # No precedence guessed between two "or"s, same discipline as the propositional grammar's
    # own refusal of a mixed/repeated connective in one clause.
    with pytest.raises(FolParseError) as excinfo:
        parse("Ravi studies or Ravi is lucky or Ravi is rich")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


def test_ground_or_is_not_a_fol_mode_signal_on_its_own() -> None:
    # Two ground facts joined by "or" still have no quantifier -- HLD S18.7's own rule (an
    # arity>0 ground predicate alone never selects FOL mode) extends unchanged to FolOr.
    assert is_fol_formula(parse("Ravi studies or Ravi is lucky")) is False


def test_ground_or_shares_the_registry_across_both_sides() -> None:
    # The cross-sentence checks (here, FOL_AMBIGUOUS_INDIVIDUAL) must see both sides of the "or",
    # not just one -- same registry, one parse call. "studies" is a predicate on the left and a
    # constant on the right: the same written word used both ways, section 18.2's own trigger.
    with pytest.raises(FolParseError) as excinfo:
        parse("Ravi studies or Studies is a person")
    assert excinfo.value.code is FolErrorCode.FOL_AMBIGUOUS_INDIVIDUAL


# ----------------------------------------------------------------------------------- wh-patterns


def test_if_x_is_a_y_then_x_is_a_z() -> None:
    result = parse("If x is a bird then x is a flyer")
    expected = ForAll(v, FolImplies(Predicate("Bird", (v,)), Predicate("Flyer", (v,))))
    assert result == expected


def test_if_name_rs_name_then_name_rs_name() -> None:
    result = parse("If Alice teaches Bob then Bob knows Alice")
    teaches = Predicate("Teach", (Constant("alice"), Constant("bob")))
    knows = Predicate("Know", (Constant("bob"), Constant("alice")))
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
    assert parse("Alice admires Bob") == Predicate("Admire", (Constant("alice"), Constant("bob")))


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


# ------------------- predicate-name canonicalization + relative/indefinite forms (2026-11-02)

# WHY these exist: the HLD section 18.9 worked example ("All students who study pass the exam.
# Ravi is a student. Ravi studies or Ravi is lucky. Anyone who is lucky passes the exam." =>
# "Ravi passes the exam") could not be parsed at all, and once it could, nothing unified --
# "students"/"student" and "study"/"studies" were different predicate symbols, so a VALID
# argument came back BUDGET_EXHAUSTED, indistinguishable to a student from "no proof exists".
# Canonicalization undoes REGULAR inflection only (-s, -es, -ies), never a word list.


def test_who_is_a_relative_pronoun_like_that() -> None:
    v = Variable("x")
    expected = ForAll(
        v,
        FolImplies(
            FolAnd((Predicate("Student", (v,)), Predicate("Study", (v,)))),
            Predicate("PassTheExam", (v,)),
        ),
    )
    assert parse("All students who study pass the exam") == expected


def test_who_and_that_produce_the_identical_formula() -> None:
    assert parse("All students who study pass the exam") == parse(
        "All students that study pass the exam"
    )


def test_anyone_who_is_a_universal_with_no_subject_class() -> None:
    v = Variable("x")
    expected = ForAll(v, FolImplies(Predicate("Lucky", (v,)), Predicate("PassTheExam", (v,))))
    assert parse("Anyone who is lucky passes the exam") == expected


def test_everyone_and_anybody_are_the_same_indefinite_form() -> None:
    assert parse("Everyone who is lucky passes the exam") == parse(
        "Anyone who is lucky passes the exam"
    )
    assert parse("Anybody who is lucky passes the exam") == parse(
        "Anyone who is lucky passes the exam"
    )


def test_indefinite_quantifier_without_a_relative_pronoun_is_refused() -> None:
    with pytest.raises(FolParseError) as excinfo:
        parse("Anyone passes the exam")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


def test_verb_plus_object_is_one_unary_predicate() -> None:
    assert parse("Ravi passes the exam") == Predicate("PassTheExam", (Constant("ravi"),))


def test_a_determiner_distinguishes_an_object_phrase_from_a_second_name() -> None:
    """ "Ravi passes the exam" is unary; "Alice likes Bob" is a binary relation. The determiner
    is the signal -- a bare name never follows the verb in the object-phrase form."""
    assert parse("Alice likes Bob") == Predicate("Like", (Constant("alice"), Constant("bob")))
    assert parse("Ravi passes the exam").args == (Constant("ravi"),)


def test_regular_plural_and_singular_are_the_same_predicate() -> None:
    registry: dict = {}
    plural = parse("All students who study pass the exam", registry)
    singular = parse("Ravi is a student", registry)
    assert singular.name == "Student"
    assert plural.body.antecedent.items[0].name == "Student"


def test_third_person_verb_and_bare_verb_are_the_same_predicate() -> None:
    registry: dict = {}
    bare = parse("All students who study pass the exam", registry)
    inflected = parse("Ravi studies", registry)
    assert inflected.name == "Study"
    assert bare.body.antecedent.items[1].name == "Study"


def test_canonicalization_merges_the_conclusion_with_the_rule() -> None:
    registry: dict = {}
    rule = parse("All students who study pass the exam", registry)
    goal = parse("Ravi passes the exam", registry)
    assert goal.name == rule.body.consequent.name == "PassTheExam"


def test_a_double_s_word_is_never_stripped_to_a_nonword() -> None:
    """ "pass" ends in s but is not a plural -- stripping it would invent "pas"."""
    assert parse("Ravi is a pass") == Predicate("Pass", (Constant("ravi"),))


def test_canonicalization_handles_a_y_plural() -> None:
    assert parse("Ravi studies") == Predicate("Study", (Constant("ravi"),))
    assert parse("Ravi flies") == Predicate("Fly", (Constant("ravi"),))


def test_canonicalization_leaves_an_uninflected_word_alone() -> None:
    assert parse("Socrates is a human") == Predicate("Human", (Constant("socrates"),))


def test_constants_are_never_canonicalized() -> None:
    """Stripping a NAME would be destructive: "Socrates" is not a plural of "Socrate"."""
    assert parse("Socrates is a human").args == (Constant("socrates"),)


def test_canonicalization_is_consistent_on_unseen_vocabulary() -> None:
    registry: dict = {}
    rule = parse("All engineers who design review the plan", registry)
    fact = parse("Priya is an engineer", registry)
    assert fact.name == "Engineer"
    assert rule.body.antecedent.items[0].name == "Engineer"


def test_canonicalization_is_consistent_on_a_second_unseen_vocabulary() -> None:
    registry: dict = {}
    rule = parse("All doctors who prescribe sign the form", registry)
    goal = parse("Meera signs the form", registry)
    assert goal.name == "SignTheForm"
    assert rule.body.consequent.name == "SignTheForm"


def test_render_shows_a_skolem_function_with_its_arguments() -> None:
    """`parse` never builds a FunctionTerm, but `render` is also handed post-Skolemization
    formulas by the CNF working display -- rendering sk_f0(x) as a bare "sk_f0" would silently
    drop the argument that makes a Skolem FUNCTION different from a Skolem constant."""
    from src.core.fol_models import FunctionTerm

    formula = Predicate("Loves", (Variable("x"), FunctionTerm("sk_f0", (Variable("x"),))))
    assert render(formula) == "Loves(x, f1(x))"  # exam notation, not the internal name


def test_render_still_shows_plain_terms_unchanged() -> None:
    assert render(Predicate("Human", (Constant("socrates"),))) == "Human(socrates)"


# --------------------- precedence-correct parenthesization (Phase 1 item 1, 2026-11-02)

# `render` joined connectives with no grouping at all, so the CNF working column printed
# "¬Student(x) ∧ Study(x) ∨ PassTheExam(x)" for ¬(Student(x) ∧ Study(x)) ∨ PassTheExam(x).
# Read as text that is a DIFFERENT formula, and in an exam it would be marked wrong.
# Precedence, tightest first: ¬ then ∧ then ∨ then → then ↔. A child looser than its parent is
# parenthesized; a child at least as tight is not, so "A ∧ B → C" stays unparenthesized.

P, Q, Z = (Predicate(n, (Variable("x"),)) for n in ("P", "Q", "Z"))


def test_negated_conjunction_is_grouped() -> None:
    assert render(FolNot(FolAnd((P, Q)))) == "¬(P(x) ∧ Q(x))"


def test_the_reported_cnf_step_renders_unambiguously() -> None:
    student = Predicate("Student", (Variable("x"),))
    study = Predicate("Study", (Variable("x"),))
    passes = Predicate("PassTheExam", (Variable("x"),))
    formula = FolOr((FolNot(FolAnd((student, study))), passes))
    assert render(formula) == "¬(Student(x) ∧ Study(x)) ∨ PassTheExam(x)"


def test_negated_disjunction_is_grouped() -> None:
    assert render(FolNot(FolOr((P, Q)))) == "¬(P(x) ∨ Q(x))"


def test_negated_implication_is_grouped() -> None:
    assert render(FolNot(FolImplies(P, Q))) == "¬(P(x) → Q(x))"


def test_a_negated_atom_needs_no_grouping() -> None:
    assert render(FolNot(P)) == "¬P(x)"


def test_an_implication_inside_a_disjunction_is_grouped() -> None:
    assert render(FolOr((FolImplies(P, Q), Z))) == "(P(x) → Q(x)) ∨ Z(x)"


def test_a_disjunction_inside_a_conjunction_is_grouped() -> None:
    assert render(FolAnd((FolOr((P, Q)), Z))) == "(P(x) ∨ Q(x)) ∧ Z(x)"


def test_a_conjunction_inside_a_disjunction_keeps_standard_precedence() -> None:
    """∧ binds tighter than ∨, so this needs no parentheses -- adding them everywhere would
    bury the reader in noise for no gain in meaning."""
    assert render(FolOr((P, FolAnd((Q, Z))))) == "P(x) ∨ Q(x) ∧ Z(x)"


def test_a_conjunction_antecedent_keeps_standard_precedence() -> None:
    assert render(FolImplies(FolAnd((P, Q)), Z)) == "P(x) ∧ Q(x) → Z(x)"


def test_an_implication_inside_a_biconditional_keeps_standard_precedence() -> None:
    """→ binds tighter than ↔, so "P → Q ↔ Z" already reads as "(P → Q) ↔ Z". Bracketing it
    would contradict the precedence this renderer documents and follows everywhere else."""
    assert render(FolIff(FolImplies(P, Q), Z)) == "P(x) → Q(x) ↔ Z(x)"


def test_a_biconditional_inside_an_implication_is_grouped() -> None:
    """The converse direction DOES need brackets: ↔ is looser than →."""
    assert render(FolImplies(FolIff(P, Q), Z)) == "(P(x) ↔ Q(x)) → Z(x)"


def test_a_quantifier_carries_its_own_grouping_under_negation() -> None:
    assert render(FolNot(ForAll(Variable("x"), P))) == "¬∀x (P(x))"


# ------------------ Skolem terms in exam notation (student instruction, 2026-11-02)

# "sk_f0" / "sk_c0" are internal counter names, as meaningless to a student as "c2_v0" was.
# A logic course writes Skolem constants C1, C2 and Skolem functions f1(x), f2(x), so the
# DISPLAY uses those. The internal names are untouched -- they are part of clause identity.


def test_a_skolem_constant_displays_in_exam_notation() -> None:
    from src.core.fol_models import Constant

    assert render(Predicate("Loves", (Constant("sk_c0"),))) == "Loves(C1)"


def test_a_skolem_function_displays_in_exam_notation() -> None:
    from src.core.fol_models import FunctionTerm

    formula = Predicate("Loves", (Variable("x"), FunctionTerm("sk_f0", (Variable("x"),))))
    assert render(formula) == "Loves(x, f1(x))"


def test_skolem_numbering_starts_at_one_not_zero() -> None:
    from src.core.fol_models import Constant, FunctionTerm

    assert render(Predicate("P", (Constant("sk_c3"),))) == "P(C4)"
    assert render(Predicate("P", (FunctionTerm("sk_f2", (Variable("x"),)),))) == "P(f3(x))"


def test_an_ordinary_constant_named_like_nothing_special_is_untouched() -> None:
    from src.core.fol_models import Constant

    assert render(Predicate("P", (Constant("skater"),))) == "P(skater)"


# ------------ verb + bare plural object is unary, not a silent binary relation (2026-11-02) -----
#
# "Aisha solves problems" (no determiner) used to fall through to the generic binary-relation
# pattern, treating "problems" as a SECOND INDIVIDUAL -- a silently WRONG parse, not a refusal.
# Fix reuses the existing regular-plural detector (_canonical_word, already built and tested) as
# the signal: a bare plural object routes to the same unary verb+object branch "the" already
# triggers. KNOWN, ACCEPTED LIMITATION: a proper name that happens to be a regular plural form
# (e.g. one ending in "-s" that _canonical_word would strip) is misread the same way -- same
# risk this project already accepted for _canonical_word itself.


def test_a_bare_plural_object_is_a_unary_predicate_not_a_second_individual() -> None:
    assert parse("Aisha solves problems") == Predicate("SolveProblem", (Constant("aisha"),))


def test_the_plural_object_reading_matches_the_determiner_reading_after_canonicalization() -> None:
    registry: dict = {}
    bare = parse("Aisha solves problems", registry)
    determined = parse("Aisha solves the problem", registry)
    # Different predicates ("SolveProblem" vs "SolveTheProblem" -- "the" is part of the phrase
    # the same way it already was before this fix), but both unary, both about one individual.
    assert bare.args == determined.args == (Constant("aisha"),)


def test_a_bare_singular_name_like_object_still_reads_as_a_binary_relation() -> None:
    """The existing, legitimate pattern -- unaffected. "Bob" is not a regular plural, so this
    still means Alice and Bob are two individuals, exactly as it always has."""
    assert parse("Alice likes Bob") == Predicate("Like", (Constant("alice"), Constant("bob")))


def test_a_modified_plural_object_is_still_unary_checked_by_its_last_word() -> None:
    assert parse("Aisha solves hard problems") == Predicate(
        "SolveHardProblem", (Constant("aisha"),)
    )


# ------------------ detect_mode: a quantifier WORD is the FOL signal (2026-11-02 fix) -----------
#
# Was: a sentence the FOL grammar could not parse AT ALL was treated as "not a FOL signal", so a
# paragraph containing a genuinely FOL-intended but currently-unsupported sentence ("All engineers
# solve problems", no copula, no relative clause) silently fell through to FULL propositional
# treatment -- Facts panel, relevance banner, none of it meant to see a quantifier. Fixed: the
# LEXICAL presence of a quantifier word is now itself the signal, whether or not this grammar's
# narrower patterns can parse the sentence. SAFE by construction: core.english's own grammar
# refuses every one of these words unconditionally (QUANTIFIER_UNSUPPORTED), so this can never
# take a sentence away from propositional that propositional would otherwise have accepted --
# there is no such sentence.


def test_an_unparseable_quantified_sentence_still_signals_fol_mode() -> None:
    # The reported live case: no copula, no relative clause -- genuinely unsupported by this
    # grammar's patterns, but unmistakably a universal claim, not an ordinary propositional fact.
    assert is_fol_sentence("All engineers solve problems") is True


def test_detect_mode_is_fol_for_the_reported_paragraph() -> None:
    sentences = ["All engineers solve problems", "Aisha is an engineer", "Aisha solves problems"]
    assert detect_mode(sentences) == "fol"


def test_every_previously_working_quantified_shape_still_signals_fol() -> None:
    """Full regression on every quantified pattern already supported tonight, both by successful
    parse (the common case) and to confirm the new lexical path does not change their outcome."""
    for sentence in (
        "Every human is mortal",  # copula
        "All students that study pass",  # relative clause, "that"
        "All students who study pass the exam",  # relative clause, "who"
        "Anyone who is lucky passes the exam",  # indefinite quantifier
        "Everyone who is lucky passes the exam",
        "Anybody who is lucky passes the exam",
        "Some student studies",
        "No cat is a dog",
    ):
        assert is_fol_sentence(sentence) is True, sentence


def test_an_ordinary_propositional_sentence_still_signals_prop() -> None:
    """No quantifier word present -- unaffected, same as always."""
    assert is_fol_sentence("Ravi is a student") is False
    assert is_fol_sentence("Alice likes Bob") is False
    assert is_fol_sentence("We get wet") is False


def test_a_genuinely_unsupported_quantifier_sentence_still_refuses_not_succeeds() -> None:
    """The detect_mode fix changes WHICH grammar reports a refusal, never whether one happens.
    "All engineers solve problems" itself is no longer a good example here -- S18.16.12's own
    bare-SVO pattern made it supported, on purpose -- so this uses a multiply-quantified relation
    instead, explicitly out of scope (S18.2) both before and after every fix tonight."""
    with pytest.raises(FolParseError):
        parse("All engineers like every manager")


def test_detect_mode_prop_for_a_sentence_that_fails_both_grammars_and_has_no_quantifier() -> None:
    """A sentence neither grammar can read, with no quantifier word either, is still prop --
    unchanged, same as the pre-existing test for this exact case."""
    assert is_fol_sentence("Blorp zorp quux") is False


# ------------------- bare "All SUBJECT verb OBJECT" quantified pattern (2026-11-02) -------------
#
# "All engineers solve problems" -- no copula, no relative clause -- was a genuine pattern gap
# (FOL_UNKNOWN_PATTERN). Reuses the EXACT signal §18.16.10's ground verb+object fix established
# (a determiner, or the object phrase's last word is a regular plural), so the two patterns can
# never disagree about what counts as an object phrase.


def test_the_reported_sentence_now_parses() -> None:
    v = Variable("x")
    expected = ForAll(v, FolImplies(Predicate("Engineer", (v,)), Predicate("SolveProblem", (v,))))
    assert parse("All engineers solve problems") == expected


def test_bare_svo_with_a_determined_object_also_parses() -> None:
    v = Variable("x")
    expected = ForAll(
        v, FolImplies(Predicate("Engineer", (v,)), Predicate("SolveTheProblem", (v,)))
    )
    assert parse("All engineers solve the problem") == expected


def test_bare_svo_with_a_modified_plural_object_parses() -> None:
    v = Variable("x")
    expected = ForAll(
        v, FolImplies(Predicate("Engineer", (v,)), Predicate("SolveHardProblem", (v,)))
    )
    assert parse("All engineers solve hard problems") == expected


def test_a_quantified_relation_to_a_named_individual_is_still_refused() -> None:
    """ "All engineers like Bob" -- a quantified relation to a NAMED individual, not an object
    phrase. Genuinely ambiguous the same way the ground pattern is; never guessed at."""
    with pytest.raises(FolParseError) as excinfo:
        parse("All engineers like Bob")
    assert excinfo.value.code is FolErrorCode.FOL_UNKNOWN_PATTERN


def test_the_relative_clause_pattern_still_takes_priority_when_present() -> None:
    """ "that"/"who" still route to the existing relative-clause reading, unaffected."""
    assert parse("All students that study pass") == parse("All students who study pass")


def test_all_with_too_few_tokens_is_still_refused() -> None:
    with pytest.raises(FolParseError):
        parse("All engineers solve")


def test_the_reported_paragraph_now_proves_end_to_end() -> None:
    from src.core.fol_search import fol_prove

    registry: dict = {}
    premises = [
        parse("All engineers solve problems", registry),
        parse("Aisha is an engineer", registry),
    ]
    goal = parse("Aisha solves problems", registry)
    result = fol_prove(premises, goal)
    from src.core.fol_search import FolProofOutcome

    assert result.outcome is FolProofOutcome.PROVED
