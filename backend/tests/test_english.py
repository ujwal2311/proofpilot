"""Tests for core.english -- the controlled grammar (docs/HLD.md sections 3 and 6.1).

Written before the implementation. Cases are drawn from the grammar audit table (HLD 17.2),
which pairs every production with a tricky counterpart.
"""

import pytest
from src.core.english import (
    And,
    Atom,
    ErrorCode,
    Iff,
    Implies,
    Not,
    Or,
    ParseError,
    parse_sentence,
    split_sentences,
)


def parse(text: str):
    return parse_sentence(text)


def raises(text: str) -> ErrorCode:
    with pytest.raises(ParseError) as caught:
        parse_sentence(text)
    return caught.value.code


# ------------------------------------------------------------------------------ normalization


def test_split_sentences_on_every_terminator() -> None:
    assert split_sentences("It rains. It is cold! Is it windy? We stay;") == [
        "It rains",
        "It is cold",
        "Is it windy",
        "We stay",
    ]


def test_split_sentences_ignores_empty_fragments() -> None:
    assert split_sentences("It rains... We stay.  ") == ["It rains", "We stay"]


def test_contraction_and_double_negation_normalized() -> None:
    # The four contractions the spec names, plus the curly apostrophe a word processor produces.
    assert parse("It isn't raining") == Atom("it is not raining")
    assert parse("The bus doesn't come") == Atom("the bus does not come")
    assert parse("It won't rain") == Atom("it will not rain")
    assert parse("We can't stay") == Atom("we can not stay")
    assert parse("It isn’t raining") == Atom("it is not raining")

    # Clause-level negation is recorded here; the fact phrase keeps its own embedded negation
    # for facts.py, and the two combine by XOR (HLD 3.3). This sentence has BOTH.
    assert parse("It is not the case that it does not rain") == Not(Atom("it does not rain"))


def test_embedded_negation_stays_inside_the_fact_phrase() -> None:
    # The layering that the grammar depends on, pinned because it is easy to get backwards.
    # `clause := ["not" | "it is not the case that"] FACT_PHRASE` -- only a LEADING negator is
    # structural. "it is not raining" has no leading negator, so it is one phrase and its
    # polarity is facts.py's business; english.py must not reach inside and split it.
    assert parse("It is not raining") == Atom("it is not raining")
    assert parse("The bus never comes") == Atom("the bus never comes")
    assert parse("No bus comes") == Atom("no bus comes")

    # Whereas a leading negator IS structural and comes out of the phrase.
    assert parse("Not it rains") == Not(Atom("it rains"))


# -------------------------------------------------------------------------------- productions


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        # 1. if cond then junction
        ("If it rains then we stay", Implies(Atom("it rains"), Atom("we stay"))),
        # 2. unless clause , junction   (sentence-initial)
        ("Unless it rains, we play", Or((Atom("we play"), Atom("it rains")))),
        # 3. clause if cond
        ("We stay if it rains", Implies(Atom("it rains"), Atom("we stay"))),
        # 4. clause only if clause
        ("We play only if it is dry", Implies(Atom("we play"), Atom("it is dry"))),
        # 5. clause unless clause
        ("We play unless it rains", Or((Atom("we play"), Atom("it rains")))),
        # 6. clause if and only if clause
        ("We play if and only if it is dry", Iff(Atom("we play"), Atom("it is dry"))),
        # 7. either or_junction
        ("Either the bus comes or we walk", Or((Atom("the bus comes"), Atom("we walk")))),
        # 8. both and_junction
        ("Both the bus comes and we walk", And((Atom("the bus comes"), Atom("we walk")))),
        # 9. neither ... nor ...
        (
            "Neither the bus comes nor we walk",
            And((Not(Atom("the bus comes")), Not(Atom("we walk")))),
        ),
        # 10. junction fallback
        ("The lights are on", Atom("the lights are on")),
        ("It is not the case that it rains", Not(Atom("it rains"))),
        ("It rains and it is cold", And((Atom("it rains"), Atom("it is cold")))),
        ("It rains or it snows", Or((Atom("it rains"), Atom("it snows")))),
    ],
)
def test_parse_each_production(sentence: str, expected) -> None:
    assert parse(sentence) == expected


def test_consequent_runs_to_end_of_sentence() -> None:
    # The correction recorded in HLD 3.2: the consequent is a junction, not a single clause,
    # or this sentence cannot be represented at all.
    assert parse("If it rains and it is cold, then we stay and we read") == Implies(
        And((Atom("it rains"), Atom("it is cold"))),
        And((Atom("we stay"), Atom("we read"))),
    )
    assert parse("If it rains, then we stay") == Implies(Atom("it rains"), Atom("we stay"))


def test_antecedent_may_be_a_junction() -> None:
    assert parse("We stay if it rains or it snows") == Implies(
        Or((Atom("it rains"), Atom("it snows"))), Atom("we stay")
    )


def test_either_and_both_are_n_ary() -> None:
    assert parse("Either we walk or we ride or we drive") == Or(
        (Atom("we walk"), Atom("we ride"), Atom("we drive"))
    )
    assert parse("Neither it rains nor it snows nor it hails") == And(
        (Not(Atom("it rains")), Not(Atom("it snows")), Not(Atom("it hails")))
    )


def test_neither_flips_a_clause_that_is_already_negated() -> None:
    # XOR, not "force negative": two STRUCTURAL negations cancel rather than stacking.
    assert parse("Neither it rains nor it is not the case that it is cold") == And(
        (Not(Atom("it rains")), Atom("it is cold"))
    )


# ------------------------------------------------------------------- keyword ordering (3.3)


def test_keyword_longest_first_ordering() -> None:
    # "if and only if" contains both "only if" and "if". Scanning for the shorter keyword first
    # would silently read this as "B if A" -- the converse -- and never report an error.
    assert parse("We play if and only if it is dry") == Iff(Atom("we play"), Atom("it is dry"))
    assert parse("We play only if it is dry") == Implies(Atom("we play"), Atom("it is dry"))
    assert parse("We play if it is dry") == Implies(Atom("it is dry"), Atom("we play"))


def test_either_neither_before_bare_or() -> None:
    # Without the prefix check, "Either A or B" would fall through to the bare junction rule and
    # leave "either the bus comes" as a fact phrase.
    assert parse("Either the bus comes or we walk") == Or((Atom("the bus comes"), Atom("we walk")))
    assert parse("Neither the bus comes nor we walk") == And(
        (Not(Atom("the bus comes")), Not(Atom("we walk")))
    )


def test_sentence_initial_unless_supported() -> None:
    assert parse("Unless it rains, we play") == parse("We play unless it rains")


def test_sentence_initial_only_if_rejected() -> None:
    # English needs subject-auxiliary inversion here ("Only if B does A happen"), which this
    # grammar cannot detect. Accepting it uninverted risks reversing the implication silently,
    # so it is refused with a specific discriminator the message layer can key on.
    with pytest.raises(ParseError) as caught:
        parse_sentence("Only if it is dry, we play")
    assert caught.value.code is ErrorCode.UNPARSEABLE
    assert caught.value.detail == "sentence_initial_only_if"


# -------------------------------------------------------------------------------- the errors


def test_ambiguous_and_or_rejected() -> None:
    assert raises("It rains and it is cold or it is windy") is ErrorCode.AMBIGUOUS_AND_OR
    # "either" forces pure-or and "both" forces pure-and; mixing inside them is still ambiguous.
    assert raises("Either it rains or it is cold and it is windy") is ErrorCode.AMBIGUOUS_AND_OR
    assert raises("Both it rains and it is cold or it is windy") is ErrorCode.AMBIGUOUS_AND_OR


def test_bracketing_prefixes_resolve_the_ambiguity() -> None:
    # The same clause list is accepted once the writer says which connective binds.
    assert parse("Both it rains and it is cold") == And((Atom("it rains"), Atom("it is cold")))
    assert parse("Either it rains or it is cold") == Or((Atom("it rains"), Atom("it is cold")))


def test_bracketing_prefix_must_match_its_own_connective() -> None:
    # The dangerous case, and the reason "either" FORCES or rather than merely hinting it.
    # Without that, "Either A and B" has only one connective present, so the generic
    # mixed-connective check passes and the sentence silently becomes a CONJUNCTION -- the
    # exact opposite of what "either" promised. Nothing downstream could detect it.
    assert raises("Either it rains and it is cold") is ErrorCode.AMBIGUOUS_AND_OR
    assert raises("Both it rains or it is cold") is ErrorCode.AMBIGUOUS_AND_OR


def test_bracketing_prefix_is_ordinary_text_without_its_connective() -> None:
    # Regression guard. An earlier fix rejected these outright, which broke "Both lights are
    # on" -- a perfectly good fact. A prefix only brackets when the connective it governs is
    # actually there; otherwise the word is phrase content, visible on the Facts screen.
    assert parse("Both lights are on") == Atom("both lights are on")
    assert parse("Either way we stay") == Atom("either way we stay")
    assert parse("Neither option works") == Atom("neither option works")


@pytest.mark.parametrize(
    "sentence",
    [
        "All buses are late",
        "Every bus is late",
        "Some buses are late",
        "Any bus is late",
        "None of the buses are late",
        "Nobody waits",
        "Everyone waits",
    ],
)
def test_quantifier_rejected(sentence: str) -> None:
    assert raises(sentence) is ErrorCode.QUANTIFIER_UNSUPPORTED


def test_paragraph_limits_rejected() -> None:
    # TOO_LONG is per-sentence; TOO_MANY_SENTENCES is paragraph-level and halts.
    # (TOO_MANY_FACTS needs fact extraction and is covered with facts.py.)
    assert raises(" ".join(["rain"] * 31)) is ErrorCode.TOO_LONG
    # Each sentence must start with a capital, or the splitter treats the full stop as an
    # abbreviation or decimal point and never breaks (HLD 3.1, the B4 rule).
    with pytest.raises(ParseError) as caught:
        split_sentences(". ".join(f"Sentence {i}" for i in range(13)))
    assert caught.value.code is ErrorCode.TOO_MANY_SENTENCES


def test_sentence_of_exactly_the_limit_is_accepted() -> None:
    # Off-by-one guard: 30 words is allowed, 31 is not.
    assert parse(" ".join(["rain"] * 30)) == Atom(" ".join(["rain"] * 30))


def test_empty_fact_phrase_rejected() -> None:
    # Syntactically empty phrases are caught here. A phrase made only of function words
    # ("it is") still has tokens, so it is caught later by facts.py when its key empties out --
    # the function-word list lives there and duplicating it would break single-source.
    assert raises("If then we stay") is ErrorCode.EMPTY_FACT_PHRASE
    assert raises("It rains and") is ErrorCode.EMPTY_FACT_PHRASE
    assert raises("not") is ErrorCode.EMPTY_FACT_PHRASE


def test_unparseable_sentence_names_itself() -> None:
    with pytest.raises(ParseError) as caught:
        parse_sentence("Only if it is dry, we play")
    assert caught.value.sentence == "Only if it is dry, we play"


# ------------------------------------------------------------- documented limitation (14.2)


def test_connective_inside_fact_mis_splits_visibly() -> None:
    # Pinned so it can never silently get worse. "bread and butter" is one noun phrase, but
    # recognising that needs a lexicon, which would be topic-specific knowledge the project
    # forbids. The Facts confirmation screen is the safety net: BOTH bogus facts are shown to
    # the user before any proving starts.
    assert parse("We sell bread and butter") == And((Atom("we sell bread"), Atom("butter")))
