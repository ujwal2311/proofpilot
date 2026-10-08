"""Tests for core.facts -- fact identity, polarity and merges (docs/HLD.md sections 3.5, 6.3).

Written before the implementation. The stemming table is the contract: every pair either merges
or appears in KNOWN_MISSES with a stated reason. There is no third option, because a silent miss
is how two different statements end up as one symbol.
"""

import random

import pytest
from src.core.english import ErrorCode, ParseError
from src.core.facts import (
    FUNCTION_WORDS,
    Fact,
    Phrase,
    canonical_key,
    extract,
    polarity,
    stem,
)

# Pairs that MUST reach the same key. Drawn from the Phase 4a plan plus the wider set used to
# check the uniform-path property.
MERGE_PAIRS = [
    ("cancelled", "cancel"),
    ("practise", "practising"),
    ("goes", "go"),
    ("studies", "study"),
    ("stopped", "stop"),
    ("falling", "fall"),
    ("classes", "class"),
    ("stays", "stay"),
    ("buses", "bus"),
    ("sees", "see"),
    ("cities", "city"),
    ("flies", "fly"),
    ("days", "day"),
    ("misses", "miss"),
    ("runs", "running"),
    ("boxes", "box"),
    ("wishes", "wish"),
    ("arrives", "arriving"),
    ("closed", "close"),
    ("opens", "opening"),
    ("carries", "carry"),
    ("delayed", "delay"),
    ("waits", "waiting"),
    ("leaves", "leave"),
    ("plays", "playing"),
    ("rains", "raining"),
    ("snows", "snowing"),
    ("works", "working"),
    ("passes", "pass"),
    ("watches", "watch"),
    ("tries", "try"),
    ("lights", "light"),
    ("buys", "buying"),
    ("sells", "selling"),
    ("holds", "holding"),
    ("rings", "ring"),
]

# Pairs the stemmer is known NOT to merge, each with the reason. Empty today; kept because an
# honest miss belongs here rather than in a deleted assertion.
KNOWN_MISSES: dict[tuple[str, str], str] = {}

# Collisions the design accepts (HLD 3.5): step 3 cannot tell a doubled consonant marking a
# short vowel from one that does not. Safe only because A1 keeps both phrases visible.
FALSE_MERGES = [("hoping", "hopping"), ("caning", "canning"), ("planed", "planned")]


# ------------------------------------------------------------------------------- the stemmer


@pytest.mark.parametrize(("left", "right"), MERGE_PAIRS)
def test_stem_table(left: str, right: str) -> None:
    if (left, right) in KNOWN_MISSES:
        assert stem(left) != stem(right), "documented miss unexpectedly merged -- update the table"
        return
    assert stem(left) == stem(right), f"{left!r} and {right!r} should share a stem"


@pytest.mark.parametrize(("left", "right"), MERGE_PAIRS + FALSE_MERGES)
def test_stem_is_idempotent(left: str, right: str) -> None:
    # The fixpoint guarantees this by construction. Without it a stem ending in "s" would be
    # stripped again on a second pass and keys would depend on how often they were computed.
    for word in (left, right):
        assert stem(stem(word)) == stem(word)


def test_every_step_applies_to_every_token() -> None:
    # The uniform-path property (HLD v2.6 A2). A base form must not skip a step just because no
    # suffix was stripped: "fall" has to reach "fal" exactly as "falling" does, or the two
    # forms land on different keys.
    assert stem("fall") == stem("falling") == "fal"
    assert stem("class") == stem("classes") == "class"
    assert stem("study") == "studi"  # y->i fires with no suffix present


def test_minimum_stem_guard_stops_short_words_vanishing() -> None:
    # Without the per-step guard the fixpoint eats short words entirely: "see" loses its "e",
    # then the bare "s" is stripped as a plural, leaving "". Every such word would then share
    # the empty key and become one fact. The guard is what stops that.
    assert stem("see") == "se"
    assert stem("sees") == "se"
    for word in ("go", "see", "sees", "is", "ox", "be"):
        assert len(stem(word)) >= 2, f"{word!r} was stemmed away to {stem(word)!r}"


def test_y_to_i_only_after_a_consonant() -> None:
    assert stem("study") == stem("studies")  # consonant before y
    assert stem("stay") == stem("stays") == "stay"  # vowel before y: unchanged
    assert stem("day") == stem("days") == "day"


@pytest.mark.parametrize(("left", "right"), FALSE_MERGES)
def test_known_false_merges_collide(left: str, right: str) -> None:
    assert stem(left) == stem(right)


def test_uniform_path_over_a_seeded_sample() -> None:
    # Shuffling the order the pairs are stemmed in must not change any result -- a guard against
    # hidden state such as a cache keyed on insertion order.
    rng = random.Random(20261008)
    shuffled = MERGE_PAIRS[:]
    rng.shuffle(shuffled)
    for left, right in shuffled:
        if (left, right) in KNOWN_MISSES:
            continue
        assert canonical_key(left) == canonical_key(right)


# ------------------------------------------------------------------------- keys and polarity


def test_function_words_are_removed() -> None:
    assert canonical_key("the bus is late") == canonical_key("a bus was late")
    assert "is" not in canonical_key("the bus is late")


def test_key_preserves_word_order() -> None:
    # Order-preserving keys stop "the dog bites the man" merging with "the man bites the dog".
    assert canonical_key("the dog bites the man") != canonical_key("the man bites the dog")


def test_empty_key_is_rejected() -> None:
    # A phrase made only of function words would otherwise produce an empty key that merges
    # with every other such phrase (HLD 3.4).
    for phrase in ("it is", "the", "a the is"):
        with pytest.raises(ParseError) as caught:
            canonical_key(phrase)
        assert caught.value.code is ErrorCode.EMPTY_FACT_PHRASE


@pytest.mark.parametrize(
    ("phrase", "positive"),
    [
        ("it rains", True),
        ("it does not rain", False),
        ("it never rains", False),
        ("no bus comes", False),
        ("it is not the case it does not rain", True),  # two tokens cancel
        ("the no-ball is called", True),  # hyphenated: one token, not a negator (A5)
        ("the well-known bus is late", True),
    ],
)
def test_polarity_counts_standalone_negation_tokens(phrase: str, positive: bool) -> None:
    assert polarity(phrase) is positive


def test_curly_apostrophe_negation_survives_the_whole_pipeline() -> None:
    # facts.py never sees raw input: contractions are expanded once, in english.py, and the
    # phrase it receives is already "it is not raining". Going through the parser is what makes
    # this a test of the pipeline rather than of a layer in isolation.
    from src.core.english import parse_sentence

    assert polarity(parse_sentence("it isn’t raining").phrase) is False
    assert polarity(parse_sentence("it is raining").phrase) is True


def test_negation_tokens_do_not_reach_the_key() -> None:
    # Polarity is extracted, so the key must be the same either way -- otherwise "it rains" and
    # "it does not rain" would be two unrelated facts instead of one fact and its negation.
    assert canonical_key("it rains") == canonical_key("it does not rain")


# ------------------------------------------------------------- extraction and symbol assignment


def test_symbols_follow_first_appearance() -> None:
    result = extract(["the bus comes", "we walk", "the bus comes"])
    assert [f.symbol for f in result.facts] == ["A", "B"]
    assert result.symbol_of["p1"] == "A"
    assert result.symbol_of["p2"] == "B"


def test_phrases_get_stable_ids_in_first_appearance_order() -> None:
    # IDs, not raw text, are what merges address (HLD v2.7 A3). Text is a poor identifier:
    # two sentences can produce the same phrase, and quoting text back breaks the moment the
    # student edits a sentence.
    result = extract(["the bus comes", "we walk"], conclusion=["we walk", "we are late"])
    assert [p.id for fact in result.facts for p in fact.phrases] == ["p1", "p2", "p3"]
    assert result.phrase_of["p1"].text == "the bus comes"
    # A phrase repeated in the conclusion is the SAME phrase, not a new id.
    assert result.phrase_of["p2"].text == "we walk"
    assert result.phrase_of["p3"].text == "we are late"


def test_auto_merged_fact_keeps_every_phrase() -> None:
    # HLD v2.6 A1: the whole point. A merge the student cannot see is a merge they cannot undo.
    result = extract(["it is hoping", "it is hopping"])
    assert len(result.facts) == 1
    assert [p.text for p in result.facts[0].phrases] == ["it is hoping", "it is hopping"]


def test_a_false_merge_is_visible_and_splittable() -> None:
    phrases = ["it is hoping", "it is hopping"]
    merged = extract(phrases)
    assert len(merged.facts) == 1, "the stemmer is expected to collide these"
    assert {p.text for p in merged.facts[0].phrases} == set(phrases), "both phrases must show"

    split = extract(phrases, merges=[("p1", "p2", "different")])
    assert len(split.facts) == 2
    assert [[p.text for p in f.phrases] for f in split.facts] == [
        ["it is hoping"],
        ["it is hopping"],
    ]
    assert [f.symbol for f in split.facts] == ["A", "B"]


def test_extraction_is_deterministic() -> None:
    phrases = ["we walk", "the bus comes", "the buses come", "we walked"]
    first = extract(phrases)
    assert first == extract(list(phrases))
    assert [f.symbol for f in first.facts] == sorted(f.symbol for f in first.facts)


# ------------------------------------------------------------------------------- merge relations


def test_merge_same_joins_two_groups() -> None:
    result = extract(
        ["the bus arrives", "the coach arrives"],
        merges=[("p1", "p2", "same")],
    )
    assert len(result.facts) == 1
    assert [p.text for p in result.facts[0].phrases] == ["the bus arrives", "the coach arrives"]
    assert result.polarity_of["p2"] is True


def test_merge_opposite_joins_and_flips_polarity() -> None:
    result = extract(
        ["the shop is open", "the shop is closed"],
        merges=[("p1", "p2", "opposite")],
    )
    assert len(result.facts) == 1
    assert result.polarity_of["p1"] is True
    assert result.polarity_of["p2"] is False


def test_merge_different_separates_a_group() -> None:
    result = extract(
        ["it is hoping", "it is hopping"],
        merges=[("p1", "p2", "different")],
    )
    assert len(result.facts) == 2


@pytest.mark.parametrize(
    ("merges", "code"),
    [
        ([("p99", "p1", "same")], ErrorCode.UNKNOWN_PHRASE),
        ([("p1", "p1", "same")], ErrorCode.SELF_MERGE),
        (
            [("p1", "p2", "same"), ("p1", "p2", "different")],
            ErrorCode.CONFLICTING_MERGE,
        ),
    ],
)
def test_invalid_merges_are_named_never_silently_overridden(merges, code) -> None:
    with pytest.raises(ParseError) as caught:
        extract(["we walk", "the bus comes"], merges=merges)
    assert caught.value.code is code


def test_conflicting_merge_detected_regardless_of_pair_order() -> None:
    # (a, b) and (b, a) are the same pair; storing them unordered is what makes this work.
    with pytest.raises(ParseError) as caught:
        extract(
            ["we walk", "the bus comes"],
            merges=[("p1", "p2", "same"), ("p2", "p1", "opposite")],
        )
    assert caught.value.code is ErrorCode.CONFLICTING_MERGE


def test_repeating_the_same_relation_is_not_a_conflict() -> None:
    result = extract(
        ["we walk", "the bus comes"],
        merges=[("p1", "p2", "same"), ("p1", "p2", "same")],
    )
    assert len(result.facts) == 1


# -------------------------------------------------------------------------- the fact ceiling


def test_too_many_facts_warns_before_merges_and_fails_after() -> None:
    # HLD v2.6 A3. Eleven distinct facts is over the limit, but a student whose paraphrases
    # inflated the count can merge down -- so before merges it is a warning, not a refusal.
    phrases = [f"fact number {n}" for n in range(11)]
    warned = extract(phrases[:10] + ["we walk"], merges=[])
    assert any("TOO_MANY_FACTS" in w for w in warned.warnings)

    merged = extract(
        phrases[:10] + ["we walk"],
        merges=[("p1", "p11", "same")],
        enforce_limit=True,
    )
    assert len(merged.facts) == 10
    assert not merged.warnings

    with pytest.raises(ParseError) as caught:
        extract(phrases[:10] + ["we walk"], merges=[], enforce_limit=True)
    assert caught.value.code is ErrorCode.TOO_MANY_FACTS


def test_fact_is_hashable_and_comparable() -> None:
    one = Fact("A", (Phrase("p1", "x"),))
    assert one == Fact("A", (Phrase("p1", "x"),))
    assert len({one, Fact("A", (Phrase("p1", "x"),))}) == 1


def test_function_word_list_is_grammar_not_topic_knowledge() -> None:
    # The anti-hardcoding principle: this list may contain only articles and auxiliaries, never
    # a word specific to any exercise's subject matter.
    assert FUNCTION_WORDS <= {
        "a",
        "an",
        "the",
        "it",
        "there",  # expletive subjects, which is why "it is" has an empty key (HLD 3.4)
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "do",
        "does",
        "did",
        "will",
        "shall",
        "would",
        "get",
        "gets",
        "got",
    }


# --------------------------------------------------------------- A6: polarity through a merge


@pytest.mark.parametrize("order", ["forward", "reversed"])
def test_opposite_merge_combined_with_embedded_negation_double_flips(order: str) -> None:
    # Two independent sign sources: the phrase's own negation, and the student declaring it the
    # opposite of another fact. They must XOR, not overwrite. "the shop is not closed" is
    # already negative; calling it the opposite of "the shop is open" flips it back to positive,
    # which is correct -- not closed IS open.
    phrases = ["the shop is open", "the shop is not closed"]
    merge = ("p1", "p2", "opposite") if order == "forward" else ("p2", "p1", "opposite")
    result = extract(phrases, merges=[merge])

    assert len(result.facts) == 1
    flipped = "p2" if order == "forward" else "p1"
    unflipped = "p1" if order == "forward" else "p2"
    # The phrase the student named SECOND is the one flipped, in either order.
    assert result.polarity_of[unflipped] is polarity(result.phrase_of[unflipped].text)
    assert result.polarity_of[flipped] is not polarity(result.phrase_of[flipped].text)


def test_conclusion_fact_absent_from_the_paragraph_warns_by_name() -> None:
    # A warning, never an error (HLD v2.7 A6): it is usually a typo, but it is also exactly what
    # a "does not follow" exercise looks like, so refusing it would make that class impossible.
    result = extract(["the bus comes"], conclusion=["we are late"])
    assert any("CONCLUSION_FACT_UNSEEN" in w and "we are late" in w for w in result.warnings)
    assert len(result.facts) == 2, "the fact is still extracted -- the warning does not drop it"


def test_conclusion_reusing_a_paragraph_fact_does_not_warn() -> None:
    assert extract(["we walk"], conclusion=["we walk"]).warnings == ()
    # And a stem-equivalent restatement counts as seen, since it is the same fact.
    assert extract(["the bus arrives"], conclusion=["the bus arrived"]).warnings == ()
