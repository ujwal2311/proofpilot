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


def phrases_of(node: Node) -> tuple[str, ...]:
    """Every fact phrase in the tree, deduplicated, in first-appearance order.

    First-appearance order, not sorted: `facts.extract` assigns phrase ids `p1, p2, …` in the
    order the student wrote them, and a merge instruction addresses those ids. Sorting here would
    renumber a student's phrases whenever they edited an earlier sentence.
    """
    match node:
        case Atom(phrase=phrase):
            return (phrase,)
        case Not(item=only):
            children: tuple[Node, ...] = (only,)
        case And(items=items) | Or(items=items):
            children = items
        case Implies(antecedent=left, consequent=right) | Iff(left=left, right=right):
            children = (left, right)
    found = [phrase for child in children for phrase in phrases_of(child)]
    return tuple(dict.fromkeys(found))


# --------------------------------------------------------------------------------- the errors


class ErrorCode(Enum):
    """Every way the text pipeline can refuse input. Shared with core.facts."""

    UNPARSEABLE = "UNPARSEABLE"
    AMBIGUOUS_AND_OR = "AMBIGUOUS_AND_OR"
    QUANTIFIER_UNSUPPORTED = "QUANTIFIER_UNSUPPORTED"
    TOO_LONG = "TOO_LONG"
    EMPTY_FACT_PHRASE = "EMPTY_FACT_PHRASE"
    TOO_MANY_SENTENCES = "TOO_MANY_SENTENCES"
    TOO_MANY_FACTS = "TOO_MANY_FACTS"
    SUSPICIOUS_FRAGMENT = "SUSPICIOUS_FRAGMENT"
    UNKNOWN_PHRASE = "UNKNOWN_PHRASE"
    SELF_MERGE = "SELF_MERGE"
    CONFLICTING_MERGE = "CONFLICTING_MERGE"
    RELEVANCE_REQUIRES_CONSISTENCY = "RELEVANCE_REQUIRES_CONSISTENCY"


class ParseError(Exception):
    """Input the text pipeline refuses -- parsing or fact extraction alike.

    One exception type for the whole pipeline, so the API layer has one thing to catch. Carries
    a code, the offending text and a machine-readable `detail`, never prose: all user-facing
    wording lives in messages.yaml so that it can be reviewed in one place.
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


def prepare(paragraph: str) -> list[str]:
    """THE entry point for external text: normalize, split on . ! ? ; strip the terminators.

    **Every** path by which text reaches core goes through this one function -- a paragraph, a
    conclusion, a CLI prompt, an `/api/parse` body, a held-out paragraph, and in M2 a typed
    formula. That is a rule rather than an observation:
    `test_every_entry_point_normalizes_alike` feeds each entry point the same messy input and
    asserts the same facts and the same verdict as the clean version, and
    `test_no_core_module_normalizes_text_itself` fails if a second normalizer appears.

    It is one function because the alternative already failed. The conclusion used to reach the
    parser raw while the paragraph went through the splitter, so a trailing full stop survived on
    the conclusion only: "we get wet." and "we get wet" became two different facts, and the
    worked example in the design review stopped following from its own premises. There is no
    second public name for this -- one normalizer with two callers is one normalizer; two names
    is a coin toss over which one a new caller picks.
    """
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

    # A one-token fragment is almost always an abbreviation the splitter mistook for a sentence
    # end ("Dr" from "Dr. Rao"). Refusing it closes the only route by which the documented
    # splitting limitation could leak a nonsense fact into a proof (HLD v2.6 A4).
    for fragment in trimmed:
        if len(fragment.split()) < 2:
            raise ParseError(ErrorCode.SUSPICIOUS_FRAGMENT, fragment, "one_token_fragment")

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


def _refuse_bad_input(tokens: list[str], sentence: str) -> None:
    """The three refusals that depend only on the token list (section 3.4).

    Cheapest and most specific first, so a student gets the most useful name for what is wrong
    rather than a blanket "unparseable".
    """
    if sum(1 for token in tokens if token != ",") > MAX_SENTENCE_WORDS:
        raise ParseError(ErrorCode.TOO_LONG, sentence)
    if QUANTIFIERS & set(tokens):
        raise ParseError(ErrorCode.QUANTIFIER_UNSUPPORTED, sentence)
    if not tokens:
        raise ParseError(ErrorCode.EMPTY_FACT_PHRASE, sentence)


def _initial_if(tokens: list[str], sentence: str, head_len: int = 1) -> Node:
    """`if cond then junction` / `if cond, junction` -- the antecedent comes first.

    `head_len` is how many leading tokens are the keyword itself: 1 for "if"/"whenever", 2 for
    "provided that"/"given that". The function never checks what the keyword actually was, so
    registering it directly for a new single-token keyword costs nothing beyond a dict entry.
    """
    split = next(
        (i for i, token in enumerate(tokens) if i >= head_len and token in (",", "then")), None
    )
    if split is None:
        raise ParseError(ErrorCode.UNPARSEABLE, sentence, "if_without_then")
    rest = split
    while rest < len(tokens) and tokens[rest] in (",", "then"):
        rest += 1
    return Implies(_junction(tokens[head_len:split], sentence), _junction(tokens[rest:], sentence))


def _initial_unless(tokens: list[str], sentence: str) -> Node:
    """`unless cond, clause` -- the supported sentence-initial form (section 3.2)."""
    split = _find(tokens, (",",))
    if split is None:
        raise ParseError(ErrorCode.UNPARSEABLE, sentence, "unless_without_comma")
    return Or((_junction(tokens[split + 1 :], sentence), _clause(tokens[1:split], sentence)))


def _initial_only(tokens: list[str], sentence: str) -> Node | None:
    """`Only if B, A` is REFUSED, not interpreted (section 3.2, limitation 6)."""
    if _find(tokens, ("only", "if")) == 0:
        raise ParseError(ErrorCode.UNPARSEABLE, sentence, "sentence_initial_only_if")
    return None


def _initial_bracketed(tokens: list[str], sentence: str) -> Node | None:
    """`either … or …` and `both … and …`.

    These words bracket only when the connective they govern is actually present. Otherwise the
    word is ordinary phrase content -- "both lights are on" is a perfectly good fact, and
    rejecting it to catch a malformed "Either it rains" would trade a common sentence for a rare
    one.
    """
    wanted, other = {"either": ("or", "and"), "both": ("and", "or")}[tokens[0]]
    if wanted in tokens[1:]:
        return _junction(tokens[1:], sentence)
    if other in tokens[1:]:
        # "Either A and B" promises a choice and delivers a conjunction. Only ONE connective is
        # present, so the generic mixed-connective check cannot see it -- without this branch the
        # sentence would parse as the OPPOSITE of what it says.
        raise ParseError(ErrorCode.AMBIGUOUS_AND_OR, sentence, f"{tokens[0]}_governs_{other}")
    return None


def _initial_neither(tokens: list[str], sentence: str) -> Node | None:
    """`neither A nor B [nor C]` -- n-ary, one negated clause each (section 3.3)."""
    if "nor" not in tokens[1:]:
        return None
    segments: list[list[str]] = [[]]
    for token in tokens[1:]:
        segments.append([]) if token == "nor" else segments[-1].append(token)
    return And(tuple(_negated(_clause(segment, sentence)) for segment in segments))


def _initial_that_clause(tokens: list[str], sentence: str) -> Node | None:
    """`provided that X, Y` / `given that X, Y` -- declines unless "that" immediately follows,
    so an ordinary fact starting with "provided"/"given" still falls through unchanged."""
    if len(tokens) > 1 and tokens[1] == "that":
        return _initial_if(tokens, sentence, head_len=2)
    return None


def _initial_not(tokens: list[str], sentence: str) -> Node | None:
    """`not both X and Y` -- NAND. Distinct from "neither X nor Y": this negates the WHOLE
    conjunction, not each clause separately. Declines for every other leading "not", which then
    falls through unchanged to `_clause`'s own single-atom negation marker."""
    if len(tokens) > 1 and tokens[1] == "both":
        if "and" in tokens[2:]:
            return Not(_junction(tokens[2:], sentence))
        if "or" in tokens[2:]:
            # Same reasoning as "both A or B" above: one connective present, mixed-check misses it.
            raise ParseError(ErrorCode.AMBIGUOUS_AND_OR, sentence, "not_both_governs_or")
    return None


# Head word -> the production it opens. A table rather than a chain of `if head == ...`: one body
# testing every sentence-initial form by hand scored 13 on mccabe, over the complexity gate. Each
# handler now reads on its own, and the DISPATCH is the thing a reader checks for completeness.
_SENTENCE_INITIAL = {
    "if": _initial_if,
    "whenever": _initial_if,
    "unless": _initial_unless,
    "only": _initial_only,
    "either": _initial_bracketed,
    "both": _initial_bracketed,
    "neither": _initial_neither,
    "provided": _initial_that_clause,
    "given": _initial_that_clause,
    "not": _initial_not,
}


def _sentence_initial(tokens: list[str], sentence: str) -> Node | None:
    """The production recognised by the FIRST word, or None if none applies.

    Separated from the infix scan because the order between them is load-bearing: a leading
    "if"/"unless" must never be read as the infix keyword of a different production. Two phases
    as two functions makes that ordering a single visible line in `parse_sentence` rather than an
    implicit property of a long body.
    """
    handler = _SENTENCE_INITIAL.get(tokens[0])
    return handler(tokens, sentence) if handler else None


def parse_sentence(sentence: str) -> Node:
    """Parse one sentence into a formula AST, or raise ParseError.

    Three phases, in an order that is a correctness requirement rather than a preference:
    refuse bad input, then the sentence-initial productions, then the infix ones. A leading
    "if"/"unless" read as an infix keyword would parse a different production silently.
    """
    tokens = _tokenize(sentence)
    _refuse_bad_input(tokens, sentence)
    if initial := _sentence_initial(tokens, sentence):
        return initial

    # Infix forms, longest keyword first. Scanning for "if" before "if and only if" would read a
    # biconditional as its converse and never report an error -- see HLD section 3.3.
    for keyword, build in (
        (("if", "and", "only", "if"), lambda left, right: Iff(left, right)),
        (("only", "if"), lambda left, right: Implies(left, right)),
        (("is", "necessary", "for"), lambda left, right: Implies(right, left)),
        (("is", "sufficient", "for"), lambda left, right: Implies(left, right)),
        (("unless",), lambda left, right: Or((left, right))),
        (("if",), lambda left, right: Implies(right, left)),
        (("implies",), lambda left, right: Implies(left, right)),
        (("otherwise",), lambda left, right: Or((left, right))),
    ):
        at = _find(tokens, keyword)
        if at is not None:
            left = _junction(tokens[:at], sentence)
            right = _junction(tokens[at + len(keyword) :], sentence)
            return build(left, right)

    return _junction(tokens, sentence)
