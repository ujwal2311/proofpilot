"""Fact identity: which phrases mean the same thing, and with what polarity.

See docs/HLD.md sections 3.5 and 6.3. A phrase becomes a canonical key by removing negation and
function words and stemming what is left; identical keys are the same fact. Nothing fuzzier than
an exact key match ever merges automatically, and every automatic merge keeps all its phrases so
the student can see it and undo it.

This module owns normalization of meaning. It owns neither sentence structure (core.english) nor
clause form (core.cnf), and it reads no files.
"""

from dataclasses import dataclass

from src.core.config import MAX_FACTS
from src.core.english import ErrorCode, ParseError, normalize_text

# Grammar, not topic knowledge: articles and auxiliaries carry no propositional content, so
# dropping them lets "the bus is late" and "a bus was late" name one fact. Adding a subject word
# here would be hardcoding, which test_no_exercise_words_in_core forbids.
FUNCTION_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "it",
        "there",  # expletive subjects: "it rains" and "rain happens" name one fact
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
)

# Only a STANDALONE token flips polarity, so "no-ball" and "well-known" are safe: the tokenizer
# keeps a hyphenated word whole (HLD v2.6 A5).
NEGATION_TOKENS = frozenset({"not", "no", "never"})

_VOWELS = "aeiou"
_MIN_STEM = 2
# No separate "ies -> i" rule: for any word ending in "ies", stripping "es" leaves exactly the
# same thing (studies -> studi), so the extra rule could never change an outcome. Mutation
# testing showed it was unreachable in effect and it was removed rather than left to look
# meaningful (docs/experiments/mutation_log.md, F9).
_SUFFIXES = (("sses", "ss"), ("ss", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", ""))


@dataclass(frozen=True)
class Phrase:
    """One fact phrase and its stable id.

    Merges address phrases by `id`, never by text: two sentences can produce the same phrase,
    and an instruction that quotes text back breaks when the student edits a sentence.
    """

    id: str
    text: str


@dataclass(frozen=True)
class Fact:
    """One proposition, and every phrase the student wrote for it."""

    symbol: str
    phrases: tuple[Phrase, ...]


@dataclass(frozen=True)
class Extraction:
    facts: tuple[Fact, ...]
    phrase_of: dict[str, Phrase]
    symbol_of: dict[str, str]  # phrase id -> symbol
    polarity_of: dict[str, bool]  # phrase id -> True when the phrase asserts its fact
    warnings: tuple[str, ...] = ()


def _keep(word: str, candidate: str) -> str:
    """Accept a step's result only if it leaves a usable stem."""
    return candidate if len(candidate) >= _MIN_STEM else word


def _suffix(word: str) -> str:
    for ending, replacement in _SUFFIXES:
        if word.endswith(ending):
            return _keep(word, word[: -len(ending)] + replacement)
    return word


def _collapse(word: str) -> str:
    """Drop one of a doubled final consonant: cancell -> cancel, stopp -> stop.

    "ss" is exempt so that class, miss and address survive intact.
    """
    doubled = len(word) >= 2 and word[-1] == word[-2] and word[-1] not in _VOWELS
    return _keep(word, word[:-1]) if doubled and word[-1] != "s" else word


def stem(word: str) -> str:
    """Reduce a word to its key form.

    Every step runs on every token, never conditionally, and the whole pipeline repeats to a
    fixpoint. Both properties are load-bearing: the uniform path is what lets a base form and an
    inflected form meet, and the fixpoint is what makes stem(stem(w)) == stem(w) -- without it,
    "buses" would stop at "bus" while "bus" went on to "bu".
    """
    for _ in range(8):
        stepped = _suffix(word)
        stepped = _keep(stepped, stepped[:-1]) if stepped.endswith("e") else stepped
        stepped = _collapse(stepped)
        if len(stepped) >= 2 and stepped[-1] == "y" and stepped[-2] not in _VOWELS:
            stepped = stepped[:-1] + "i"  # study -> studi, but stay is left alone
        if stepped == word:
            return word
        word = stepped
    return word


def _tokens(phrase: str) -> list[str]:
    return normalize_text(phrase).lower().split()


def polarity(phrase: str) -> bool:
    """True if the phrase asserts its fact, False if it denies it.

    Counts standalone negation tokens, so an even number cancels: "it is not the case it does
    not rain" is positive. The structural Not from the parser is XORed with this by the caller.
    """
    return sum(1 for token in _tokens(phrase) if token in NEGATION_TOKENS) % 2 == 0


def canonical_key(phrase: str) -> tuple[str, ...]:
    """Order-preserving tuple of stems, with negation and function words removed.

    Order is preserved so that "the dog bites the man" and "the man bites the dog" stay apart;
    a set would merge them.
    """
    key = tuple(
        stem(token)
        for token in _tokens(phrase)
        if token not in NEGATION_TOKENS and token not in FUNCTION_WORDS
    )
    if not key:
        raise ParseError(ErrorCode.EMPTY_FACT_PHRASE, phrase, "only_function_words")
    return key


def _validate(merges, known: set[str]) -> list[tuple[str, str, str]]:
    """Check the student's merge decisions, keeping the order they named the phrases in.

    Conflicts are detected on the UNORDERED pair, because (a, b) and (b, a) are the same
    decision. The returned list keeps the original order, because "opposite" is directional --
    it flips the second phrase relative to the first, and sorting would flip the wrong one.
    """
    seen: dict[frozenset[str], str] = {}
    checked: list[tuple[str, str, str]] = []
    for a, b, relation in merges:
        if a == b:
            raise ParseError(ErrorCode.SELF_MERGE, a, "merged_with_itself")
        for side in (a, b):
            if side not in known:
                raise ParseError(ErrorCode.UNKNOWN_PHRASE, side, "no_sentence_produced_it")
        pair = frozenset({a, b})
        if seen.get(pair, relation) != relation:
            raise ParseError(ErrorCode.CONFLICTING_MERGE, f"{a} / {b}", "two_relations_one_pair")
        if pair not in seen:
            checked.append((a, b, relation))
        seen[pair] = relation
    return checked


def extract(phrases, conclusion=(), merges=(), enforce_limit: bool = False) -> Extraction:
    """Group phrases into facts, assign symbols and ids, and resolve polarity.

    `phrases` come from the paragraph and `conclusion` from the claimed conclusion; ids run
    `p1, p2, …` across both in that order. `merges` are the student's decisions as
    (phrase id, phrase id, relation) triples.

    Symbols are re-assigned from scratch on every call, so the result is a pure function of its
    inputs and never depends on what was merged before. That is also why changing a merge
    discards downstream progress (HLD v2.7 A4): the symbols a proof was built on may no longer
    mean the same thing.

    `enforce_limit` is False on the first pass so a student whose paraphrases inflate the count
    gets a warning and a chance to merge, rather than a refusal (HLD v2.6 A3).
    """
    texts = list(dict.fromkeys([*phrases, *conclusion]))
    ordered = [Phrase(f"p{n}", text) for n, text in enumerate(texts, start=1)]
    phrase_of = {p.id: p for p in ordered}
    relations = _validate(merges, set(phrase_of))

    group_of = {p.id: canonical_key(p.text) for p in ordered}
    flipped: set[str] = set()
    for a, b, relation in relations:
        if relation == "different":
            # Force b out of whatever group it shares, using a key no phrase can produce.
            group_of[b] = (*group_of[b], "\x00split", b)
        else:
            group_of[b] = group_of[a]
            if relation == "opposite":
                flipped.add(b)  # the SECOND phrase is the one the student called the opposite

    grouped: dict[tuple[str, ...], list[Phrase]] = {}
    for p in ordered:
        grouped.setdefault(group_of[p.id], []).append(p)

    facts = tuple(
        Fact(chr(ord("A") + index), tuple(members))
        for index, members in enumerate(grouped.values())
    )
    symbol_of = {p.id: fact.symbol for fact in facts for p in fact.phrases}
    # Two independent sign sources -- the phrase's own negation and an "opposite" merge -- XOR.
    polarity_of = {p.id: polarity(p.text) != (p.id in flipped) for p in ordered}

    warnings: list[str] = []
    from_paragraph = {symbol_of[p.id] for p in ordered if p.text in set(phrases)}
    for p in ordered:
        if p.text not in set(phrases) and symbol_of[p.id] not in from_paragraph:
            # A warning, never an error: usually a typo, but also exactly what a
            # "does not follow" exercise looks like (HLD v2.7 A6).
            warnings.append(f"CONCLUSION_FACT_UNSEEN: {p.text!r} appears in no premise")

    if len(facts) > MAX_FACTS:
        if enforce_limit:
            raise ParseError(ErrorCode.TOO_MANY_FACTS, f"{len(facts)} facts", "after_merges")
        warnings.append(f"TOO_MANY_FACTS: {len(facts)} facts, limit {MAX_FACTS}; merge to continue")
    return Extraction(facts, phrase_of, symbol_of, polarity_of, tuple(warnings))
