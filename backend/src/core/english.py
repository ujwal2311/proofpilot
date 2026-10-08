"""The controlled-English grammar: text in, formula AST out.

See docs/HLD.md sections 3 and 6.1. The grammar's defining property is that a *clause* never
contains a connective, so every sentence has at most one top-level connective construct and
every "and"/"or" token is by definition top-level. That is what reduces parsing to a single
left-to-right scan with no backtracking -- and it is also the system's biggest limitation,
because a connective inside a noun phrase ("bread and butter") splits (HLD section 14.2).

This module owns normalization, the keyword scan and the AST. It owns neither fact identity
(core.facts) nor clause form (core.cnf), and it never guesses: anything outside the grammar
raises with a named code.
"""

from dataclasses import dataclass
from enum import Enum

from src.core.config import MAX_SENTENCE_WORDS, MAX_SENTENCES

# ------------------------------------------------------------------------------------ the AST


@dataclass(frozen=True)
class Atom:
    """One fact phrase, verbatim. Its own embedded negation is resolved later by core.facts."""

    phrase: str


@dataclass(frozen=True)
class Not:
    item: "Node"


@dataclass(frozen=True)
class And:
    items: tuple["Node", ...]


@dataclass(frozen=True)
class Or:
    items: tuple["Node", ...]


@dataclass(frozen=True)
class Implies:
    antecedent: "Node"
    consequent: "Node"


@dataclass(frozen=True)
class Iff:
    left: "Node"
    right: "Node"


Node = Atom | Not | And | Or | Implies | Iff


# --------------------------------------------------------------------------------- the errors


class ErrorCode(Enum):
    UNPARSEABLE = "UNPARSEABLE"
    AMBIGUOUS_AND_OR = "AMBIGUOUS_AND_OR"
    QUANTIFIER_UNSUPPORTED = "QUANTIFIER_UNSUPPORTED"
    TOO_LONG = "TOO_LONG"
    EMPTY_FACT_PHRASE = "EMPTY_FACT_PHRASE"
    TOO_MANY_SENTENCES = "TOO_MANY_SENTENCES"
    TOO_MANY_FACTS = "TOO_MANY_FACTS"


class ParseError(Exception):
    """A sentence outside the supported language.

    Carries a code, the offending sentence and a machine-readable `detail`, never prose: all
    user-facing wording lives in messages.yaml so that it can be reviewed in one place.
    """

    def __init__(self, code: ErrorCode, sentence: str, detail: str = "") -> None:
        super().__init__(f"{code.value}: {sentence!r}")
        self.code = code
        self.sentence = sentence
        self.detail = detail


# --------------------------------------------------------------------------------- vocabulary

CONTRACTIONS = {
    "isn't": "is not",
    "doesn't": "does not",
    "won't": "will not",
    "can't": "can not",
}
# Compound indefinites are the same phenomenon as the bare forms and are listed explicitly:
# token matching means "everyone" would not be caught by "every", and accepting it would turn a
# quantified claim into a propositional atom that silently misrepresents it (HLD v2.5 change 3).
QUANTIFIERS = frozenset(
    {
        "all",
        "every",
        "some",
        "any",
        "none",
        "nobody",
        "everyone",
        "someone",
        "somebody",
        "anyone",
        "anybody",
        "everybody",
        "something",
        "anything",
        "everything",
        "nothing",
    }
)
NEGATORS = (("it", "is", "not", "the", "case", "that"), ("not",))
_TERMINATORS = ".!?;"

# Characters a word processor substitutes silently. Normalized in ONE place, before anything
# else looks at the text: a curly apostrophe that survives to the contraction table turns
# "isn't" into a content word and the negation is lost on the way to facts.py.
_UNICODE_FOLD = {
    "‘": "'",
    "’": "'",  # curly single quotes
    "“": '"',
    "”": '"',  # curly double quotes
    "–": "-",
    "—": "-",  # en and em dashes
    " ": " ",
    " ": " ",
    " ": " ",  # non-breaking spaces
}


def normalize_text(text: str) -> str:
    """Fold typographic characters to ASCII. Idempotent; the single entry point for text."""
    return "".join(_UNICODE_FOLD.get(char, char) for char in text)


def _is_break(text: str, index: int) -> bool:
    """Is the terminator at `index` a sentence end, rather than a decimal point or abbreviation?

    A terminator breaks only when the next non-space character is uppercase, or when nothing
    follows. One rule covers both cases the design calls out: "e.g." is followed by a lowercase
    letter, and a decimal point is followed by a digit, which is not uppercase either -- so
    numbers need no special case. "Dr. Rao" still splits; telling it apart from a real sentence
    end needs an abbreviation lexicon, which is topic knowledge the project forbids, so the
    fragment is left visible on the Facts screen instead (HLD section 14).
    """
    rest = text[index + 1 :].lstrip()
    return not rest or rest[0].isupper()


def split_sentences(paragraph: str) -> list[str]:
    """Split a paragraph into sentences on . ! ? ; discarding empty fragments."""
    text = normalize_text(paragraph)
    sentences: list[str] = []
    current = ""
    for index, char in enumerate(text):
        if char in _TERMINATORS and _is_break(text, index):
            sentences.append(current)
            current = ""
        else:
            current += char
    sentences.append(current)

    trimmed = [stripped for s in sentences if (stripped := s.strip(" \t\n" + _TERMINATORS))]
    if len(trimmed) > MAX_SENTENCES:
        raise ParseError(ErrorCode.TOO_MANY_SENTENCES, paragraph, f"{len(trimmed)} sentences")
    return trimmed


def _tokenize(sentence: str) -> list[str]:
    """Fold Unicode, lowercase, expand contractions, and make commas separate tokens."""
    text = normalize_text(sentence).lower()
    for short, long in CONTRACTIONS.items():
        text = text.replace(short, long)
    return [token for token in text.replace(",", " , ").split() if token]


def _find(tokens: list[str], phrase: tuple[str, ...], start: int = 0) -> int | None:
    """Index of the first occurrence of a token sequence, or None."""
    for i in range(start, len(tokens) - len(phrase) + 1):
        if tuple(tokens[i : i + len(phrase)]) == phrase:
            return i
    return None


# ---------------------------------------------------------------------------------- the parse


def _negated(node: Node) -> Node:
    """Flip a clause's polarity. Two negations cancel rather than stacking."""
    return node.item if isinstance(node, Not) else Not(node)


def _clause(tokens: list[str], sentence: str) -> Node:
    """["not" | "it is not the case that"] FACT_PHRASE."""
    negate = False
    for marker in NEGATORS:
        if tuple(tokens[: len(marker)]) == marker:
            tokens, negate = tokens[len(marker) :], True
            break
    phrase = " ".join(token for token in tokens if token != ",")
    if not phrase:
        raise ParseError(ErrorCode.EMPTY_FACT_PHRASE, sentence)
    atom = Atom(phrase)
    return Not(atom) if negate else atom


def _junction(tokens: list[str], sentence: str) -> Node:
    """clause (("and"|"or") clause)* -- every and/or token is top-level, by construction.

    Mixing connectives is refused rather than resolved by precedence: any precedence rule here
    would be the parser guessing what the writer meant.
    """
    present = {token for token in tokens if token in ("and", "or")}
    if len(present) > 1:
        raise ParseError(ErrorCode.AMBIGUOUS_AND_OR, sentence)

    operator = present.pop() if present else None
    if operator is None:
        return _clause(tokens, sentence)

    segments: list[list[str]] = [[]]
    for token in tokens:
        segments.append([]) if token == operator else segments[-1].append(token)
    items = tuple(_clause(segment, sentence) for segment in segments)
    return And(items) if operator == "and" else Or(items)


def parse_sentence(sentence: str) -> Node:
    """Parse one sentence into a formula AST, or raise ParseError.

    Checks run cheapest-and-most-specific first so the student gets the most useful name for
    what is wrong, rather than a blanket "unparseable".
    """
    tokens = _tokenize(sentence)
    if sum(1 for token in tokens if token != ",") > MAX_SENTENCE_WORDS:
        raise ParseError(ErrorCode.TOO_LONG, sentence)
    if QUANTIFIERS & set(tokens):
        raise ParseError(ErrorCode.QUANTIFIER_UNSUPPORTED, sentence)
    if not tokens:
        raise ParseError(ErrorCode.EMPTY_FACT_PHRASE, sentence)

    # Sentence-initial forms, checked before any infix scan so that a leading "if"/"unless" is
    # never mistaken for the infix keyword of a different production.
    head = tokens[0]
    if head == "if":
        split = next((i for i, token in enumerate(tokens) if i and token in (",", "then")), None)
        if split is None:
            raise ParseError(ErrorCode.UNPARSEABLE, sentence, "if_without_then")
        rest = split
        while rest < len(tokens) and tokens[rest] in (",", "then"):
            rest += 1
        return Implies(_junction(tokens[1:split], sentence), _junction(tokens[rest:], sentence))
    if head == "unless":
        split = _find(tokens, (",",))
        if split is None:
            raise ParseError(ErrorCode.UNPARSEABLE, sentence, "unless_without_comma")
        return Or((_junction(tokens[split + 1 :], sentence), _clause(tokens[1:split], sentence)))
    if head == "only" and _find(tokens, ("only", "if")) == 0:
        raise ParseError(ErrorCode.UNPARSEABLE, sentence, "sentence_initial_only_if")
    # "either"/"both"/"neither" act as bracketing prefixes only when the connective they govern
    # is actually present. Otherwise the word is ordinary phrase content -- "both lights are on"
    # is a perfectly good fact, and rejecting it to catch a malformed "Either it rains" would
    # trade a common sentence for a rare one.
    for prefix, wanted, other in (("either", "or", "and"), ("both", "and", "or")):
        if head != prefix:
            continue
        if wanted in tokens[1:]:
            return _junction(tokens[1:], sentence)
        if other in tokens[1:]:
            # "Either A and B" promises a choice and delivers a conjunction. Only one
            # connective is present, so the generic mixed-connective check cannot see it --
            # without this branch the sentence would parse as the OPPOSITE of what it says.
            raise ParseError(ErrorCode.AMBIGUOUS_AND_OR, sentence, f"{prefix}_governs_{other}")
    if head == "neither" and "nor" in tokens[1:]:
        segments: list[list[str]] = [[]]
        for token in tokens[1:]:
            segments.append([]) if token == "nor" else segments[-1].append(token)
        return And(tuple(_negated(_clause(segment, sentence)) for segment in segments))

    # Infix forms, longest keyword first. Scanning for "if" before "if and only if" would read a
    # biconditional as its converse and never report an error -- see HLD section 3.3.
    for keyword, build in (
        (("if", "and", "only", "if"), lambda left, right: Iff(left, right)),
        (("only", "if"), lambda left, right: Implies(left, right)),
        (("unless",), lambda left, right: Or((left, right))),
        (("if",), lambda left, right: Implies(right, left)),
    ):
        at = _find(tokens, keyword)
        if at is not None:
            left = _junction(tokens[:at], sentence)
            right = _junction(tokens[at + len(keyword) :], sentence)
            return build(left, right)

    return _junction(tokens, sentence)
