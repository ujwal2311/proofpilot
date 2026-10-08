"""Robustness and round-trip tests for core.english (docs/HLD.md sections 3, 6.1, 14).

Separate from test_english.py, which pins the grammar productions. This file attacks the edges:
word boundaries, Unicode, sentence splitting, degenerate input, and a seeded round-trip property
test. Written before the fixes they motivated.
"""

import random

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


# ------------------------------------------------------------------ B2: word boundaries


@pytest.mark.parametrize(
    "sentence",
    [
        "the gift is wrapped",  # "if" inside "gift"
        "the doctor is in",  # "or" inside "doctor"
        "the band plays",  # "and" inside "band"
        "the company is open",  # "or"/"an" inside "company"
        "the team then practises",  # a bare "then" with no "if"
        "the north gate is shut",  # "nor" inside "north"
        "the bother is real",  # "both" inside "bother"
        "it is neither here",  # "neither" IS a keyword -- see the separate assertion below
    ][:-1],
)
def test_connectives_match_whole_words_only(sentence: str) -> None:
    # Keyword matching is token-based, so a keyword appearing as a SUBSTRING of a content word
    # must never trigger a production. A substring match here would silently restructure the
    # sentence and no downstream stage could detect it.
    assert parse(sentence) == Atom(sentence)


@pytest.mark.parametrize(
    ("sentence", "rejected"),
    [
        ("Everyone waits", True),
        ("Every bus is late", True),
        ("Someone waits", True),
        ("Anyone waits", True),
        ("Something breaks", True),
        ("Anything breaks", True),
        ("Everything breaks", True),
        ("The everyday bus is late", False),  # "every" inside "everyday"
        ("The anyway sign is up", False),  # "any" inside "anyway"
        ("The somewhere sign is up", False),  # "some" inside "somewhere"
    ],
)
def test_quantifiers_match_whole_words_only(sentence: str, rejected: bool) -> None:
    if rejected:
        assert raises(sentence) is ErrorCode.QUANTIFIER_UNSUPPORTED
    else:
        assert isinstance(parse(sentence), Atom)


# -------------------------------------------------------------- B3: Unicode normalization


@pytest.mark.parametrize(
    ("raw", "expected_phrase"),
    [
        ("it isn’t raining", "it is not raining"),  # curly apostrophe
        ("it isn't raining", "it is not raining"),  # straight apostrophe
        ("it is not raining", "it is not raining"),  # non-breaking spaces
        ("the bus – the red one – is late", "the bus - the red one - is late"),  # en dash
        ("the bus — the red one — is late", "the bus - the red one - is late"),  # em dash
        ("the “fast” bus is late", 'the "fast" bus is late'),  # curly double quotes
        ("the ‘fast’ bus is late", "the 'fast' bus is late"),  # curly single quotes
    ],
)
def test_unicode_is_normalized_before_contraction_expansion(raw: str, expected_phrase: str) -> None:
    # Order matters: a curly apostrophe must become straight BEFORE contractions are expanded,
    # or "isn’t" survives as a content word and its negation is lost on the way to facts.py.
    assert parse(raw) == Atom(expected_phrase)


def test_curly_apostrophe_keeps_its_negation_through_to_the_fact_layer() -> None:
    # The whole point of B3: the phrase handed to facts.py must still contain "not".
    assert "not" in parse("it isn’t raining").phrase.split()


# --------------------------------------------------------------- B4: sentence splitting


@pytest.mark.parametrize(
    ("paragraph", "expected"),
    [
        # A terminator splits only at whitespace + uppercase, or at end of text.
        ("It rains. We stay.", ["It rains", "We stay"]),
        ("It rains. We stay", ["It rains", "We stay"]),  # missing final punctuation
        ("The gap is 3.5 metres", ["The gap is 3.5 metres"]),  # never inside a number
        ("It costs 1,000.50 today", ["It costs 1,000.50 today"]),
        ("We stay, e.g. today. It rains.", ["We stay, e.g. today", "It rains"]),  # lowercase after
        ("It rains... We stay.", ["It rains", "We stay"]),  # ellipsis is one break
        ("It rains!  We stay?  Yes;", ["It rains", "We stay", "Yes"]),
        ("", []),
        ("   ", []),
        ("...", []),
        (".!?;", []),
    ],
)
def test_sentence_splitting_rules(paragraph: str, expected: list[str]) -> None:
    assert split_sentences(paragraph) == expected


def test_abbreviation_before_a_capital_splits_and_is_documented() -> None:
    # Honest limitation, pinned so it cannot silently change: "Dr." looks exactly like a sentence
    # end. Distinguishing them needs an abbreviation lexicon, which is topic knowledge the
    # project forbids. The fragment is visible on the Facts screen, like "bread and butter".
    assert split_sentences("Dr. Rao arrives.") == ["Dr", "Rao arrives"]


# -------------------------------------------------------------------- B5: degenerate input


@pytest.mark.parametrize("raw", ["", "   ", "  ", ",", ",,,"])
def test_empty_and_punctuation_only_input_is_rejected(raw: str) -> None:
    assert raises(raw) is ErrorCode.EMPTY_FACT_PHRASE


@pytest.mark.parametrize(
    ("upper", "lower"),
    [
        ("IF it rains THEN we stay", "if it rains then we stay"),
        ("UNLESS it rains, we play", "unless it rains, we play"),
        ("EITHER it rains OR it snows", "either it rains or it snows"),
        ("Neither It Rains Nor It Snows", "neither it rains nor it snows"),
    ],
)
def test_keywords_are_case_insensitive(upper: str, lower: str) -> None:
    assert parse(upper) == parse(lower)


def test_repeated_whitespace_collapses() -> None:
    assert parse("it    rains   and\tit  is cold") == And((Atom("it rains"), Atom("it is cold")))


def test_trailing_then_leaves_an_empty_consequent() -> None:
    assert raises("If it rains then") is ErrorCode.EMPTY_FACT_PHRASE
    assert raises("If then we stay") is ErrorCode.EMPTY_FACT_PHRASE


def test_sentence_length_boundary() -> None:
    assert isinstance(parse(" ".join(["rain"] * 30)), Atom)
    assert raises(" ".join(["rain"] * 31)) is ErrorCode.TOO_LONG


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("we stay and we read", And((Atom("we stay"), Atom("we read")))),
        ("we stay or we read", Or((Atom("we stay"), Atom("we read")))),
        ("it is not the case that we stay", Not(Atom("we stay"))),
    ],
)
def test_a_conclusion_may_be_compound(conclusion: str, expected) -> None:
    # A conclusion is parsed by the same grammar as any other sentence. Negating it for the
    # refutation is cnf.py's job, which is why a compound conclusion needs no special case here.
    assert parse(conclusion) == expected


# ----------------------------------------------------- B6: seeded round-trip property test

# Keyword-free filler words, so a generated phrase can never accidentally contain a connective.
_WORDS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")


def _render(node) -> str:
    """Canonical English for an AST. Bare junctions only -- "both"/"either" are sentence-initial
    prefixes and are not part of `cond`, so using them inside an implication would be outside
    the grammar (see the documented limitation in test_both_inside_a_condition)."""
    match node:
        case Atom(phrase):
            return phrase
        case Not(item):
            return f"it is not the case that {_render(item)}"
        case And(items):
            return " and ".join(_render(i) for i in items)
        case Or(items):
            return " or ".join(_render(i) for i in items)
        case Implies(antecedent, consequent):
            return f"if {_render(antecedent)} then {_render(consequent)}"
        case Iff(left, right):
            return f"{_render(left)} if and only if {_render(right)}"
    raise AssertionError(f"unrenderable node: {node!r}")


def _random_ast(rng: random.Random):
    def phrase() -> str:
        return " ".join(rng.sample(_WORDS, rng.randint(1, 3)))

    def clause():
        atom = Atom(phrase())
        return Not(atom) if rng.random() < 0.3 else atom

    def junction():
        roll = rng.random()
        if roll < 0.5:
            return clause()
        items = tuple(clause() for _ in range(rng.randint(2, 3)))
        return And(items) if roll < 0.75 else Or(items)

    roll = rng.random()
    if roll < 0.4:
        return junction()
    if roll < 0.8:
        return Implies(junction(), junction())
    return Iff(clause(), clause())


def test_round_trip_render_then_parse_is_identity() -> None:
    # Every grammar shape, rendered to English and read back, must produce the same AST. This
    # catches whole classes of defect a hand-written fixture never reaches -- keyword
    # collisions, splitting errors, and negation that stacks instead of cancelling.
    #
    # Samples over the 30-word limit are redrawn rather than counted as failures: the limit is
    # a documented part of the language, so a sentence that breaches it is out of scope for a
    # round-trip property, not evidence of a parser defect.
    rng = random.Random(20261008)
    failures: list[tuple[str, str]] = []
    checked = 0
    for _ in range(20_000):
        if checked == 300:
            break
        node = _random_ast(rng)
        sentence = _render(node)
        if len(sentence.split()) > 30:
            continue
        checked += 1
        try:
            parsed = parse_sentence(sentence)
        except ParseError as error:
            failures.append((sentence, f"{error.code.value}/{error.detail}"))
            continue
        if parsed != node:
            failures.append((sentence, f"got {parsed!r}"))
    assert checked == 300, f"generator produced only {checked} in-scope cases"
    assert not failures, f"{len(failures)} round-trip failures, first 5: {failures[:5]}"


def test_both_inside_a_condition_is_a_documented_limitation() -> None:
    # "both"/"either" are sentence-initial prefixes; `cond := junction` does not admit them.
    # Inside an implication they are therefore read as part of the fact phrase. Pinned rather
    # than fixed: rejecting the word outright would break a legitimate phrase such as
    # "both lights are on".
    assert parse("if both alpha and bravo then charlie") == Implies(
        And((Atom("both alpha"), Atom("bravo"))), Atom("charlie")
    )
    # And the reason it is pinned rather than fixed: the word is legitimate phrase content.
    assert parse("both lights are on") == Atom("both lights are on")
