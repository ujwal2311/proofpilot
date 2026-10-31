"""The controlled FOL grammar: text in, FolFormula AST out.

See docs/HLD.md section 18.2. Same design principles as core.english: bounded, documented,
refused -- only the patterns listed below are parsed, anything else raises FolParseError with a
named code and no attempt to guess a meaning. No NLP library: pure token scan, same approach as
the propositional grammar, reusing its Unicode normalization (not its AST -- Predicate has typed
term arguments where Atom has a raw phrase, so the two type unions stay separate per HLD S18.1).

SUPPORTED PATTERNS (HLD section 18.2.2):
  Quantified : "Every X is a Y" / "Every X is not a Y" / "Some X is a Y" / "No X is a Y" /
               "All X that Y are Z"
  Ground     : "NAME Rs NAME" / "NAME Rs NAME and NAME" / "NAME is a Y" / "NAME is not a Y"
  Wh         : "If X is a Y then X is a Z" / "If NAME Rs NAME then NAME Rs NAME"

GRAMMAR LIMITATIONS, stated rather than hidden (HLD section 18.2's own out-of-scope note, plus
two more this implementation adds explicitly):
  - No stemming/lemmatization, same choice core.english makes for facts: "students" and "student"
    are different predicate symbols unless written identically. Merging them would be a guess
    about what the writer meant.
  - The unary-predicate slot after "is"/"is not" is read as EVERYTHING remaining in the sentence,
    CamelCase-joined -- "every human is mortal" strips "is" and reads "mortal"; "some student
    studies" has no "is" to strip and reads "studies" directly. Both are one documented rule, not
    two different ones.
  - A relation verb must be a single word that is NOT "is" -- "is" is reserved for the copula
    patterns. A multi-word relation starting with "is" ("is taller than") is consequently out of
    scope for the SENTENCE patterns, even though HLD section 18.2.3 uses it as a normalization
    example; disambiguating it from a copula without guessing would need more grammar than the
    bounded design budgets for.
  - Equality ("equals", "is the same as") is refused by name (FOL_UNSUPPORTED_ARITY), never parsed.
  - Every name/predicate/relation slot is checked against the reserved-word list below (added
    during implementation, not in the original design note): without it, a malformed sentence
    like "Every human likes every dog" would silently CamelCase "likes every dog" into one bogus
    predicate instead of being refused -- exactly the silent-guess failure mode CLAUDE.md
    principle 2 exists to prevent.

CROSS-SENTENCE CHECKS (FOL_AMBIGUOUS_INDIVIDUAL, FOL_UNSUPPORTED_ARITY's arity half): neither
error is detectable from one sentence alone, so `parse()` takes an optional `registry` the
caller threads across every sentence of one paragraph. English never spells a bound variable's
name, so "a name used both as a constant and a variable" (HLD section 18.2.4's literal wording)
is read here as its implementable equivalent: the same written word used once as an individual
and once as a predicate/relation class -- e.g. "Alice likes Bob" then "Every alice is nice" --
which is the one way a role clash can actually arise from text.
"""

from enum import Enum

from src.core.config import MAX_SENTENCE_WORDS
from src.core.english import normalize_text
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolFormula,
    FolIff,
    FolImplies,
    FolNot,
    FolOr,
    ForAll,
    Predicate,
    Variable,
)

Registry = dict[str, tuple[str, int]]  # written word/phrase -> (role, arity); role "const"/"pred"


class FolErrorCode(Enum):
    FOL_UNKNOWN_PATTERN = "FOL_UNKNOWN_PATTERN"
    FOL_NESTED_QUANTIFIER_IN_GROUND = "FOL_NESTED_QUANTIFIER_IN_GROUND"
    FOL_AMBIGUOUS_INDIVIDUAL = "FOL_AMBIGUOUS_INDIVIDUAL"
    FOL_UNSUPPORTED_ARITY = "FOL_UNSUPPORTED_ARITY"
    FOL_SENTENCE_TOO_LONG = "FOL_SENTENCE_TOO_LONG"


class FolParseError(Exception):
    """One exception type for the FOL grammar, same shape as core.english.ParseError: a code, the
    offending text, and a machine-readable detail -- never prose (messages.yaml owns wording)."""

    def __init__(self, code: FolErrorCode, sentence: str, detail: str = "") -> None:
        super().__init__(f"{code.value}: {sentence!r}")
        self.code = code
        self.sentence = sentence
        self.detail = detail


_QUANTIFIERS = ("every", "all", "some", "no")
_RESERVED = frozenset(
    {"every", "all", "some", "no", "and", "that", "if", "then", "is", "not", "a", "an", "are"}
)
_EQUALITY_MARKERS = (("equals",), ("is", "the", "same", "as"))


def _tokenize(sentence: str) -> list[str]:
    return [token for token in normalize_text(sentence).lower().split() if token]


def _camel_case(words: list[str]) -> str:
    """CamelCase-join words into one predicate or relation name: ["is","taller","than"] ->
    "IsTallerThan", ["human"] -> "Human" (HLD section 18.2.3)."""
    return "".join(word.capitalize() for word in words)


def _check_reserved(words: list[str], sentence: str) -> None:
    """Refuse a name/predicate phrase that is, or contains, a structural keyword -- the guard
    that keeps a malformed sentence from being silently CamelCased into a bogus predicate (see
    the module docstring's limitations list)."""
    if any(word in _QUANTIFIERS for word in words):
        raise FolParseError(FolErrorCode.FOL_NESTED_QUANTIFIER_IN_GROUND, sentence)
    if any(word in _RESERVED for word in words):
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)


def _register(registry: Registry, word: str, role: str, arity: int, sentence: str) -> None:
    """Record `word`'s role and arity, or raise if this use conflicts with an earlier one.

    Keyed by the RAW written word/phrase, before CamelCasing or lowercasing to a constant -- that
    is the only form in which "Alice" (a name) and "alice" (a class, once CamelCased to "Alice")
    would otherwise silently look unrelated despite being the same written word.
    """
    seen = registry.get(word)
    if seen is None:
        registry[word] = (role, arity)
        return
    seen_role, seen_arity = seen
    if seen_role != role:
        raise FolParseError(FolErrorCode.FOL_AMBIGUOUS_INDIVIDUAL, sentence, word)
    if seen_arity != arity:
        raise FolParseError(FolErrorCode.FOL_UNSUPPORTED_ARITY, sentence, word)


def _constant(word: str, registry: Registry, sentence: str) -> Constant:
    _check_reserved([word], sentence)
    _register(registry, word, "const", 0, sentence)
    return Constant(word)


def _predicate(
    words: list[str], args: tuple[object, ...], registry: Registry, sentence: str
) -> Predicate:
    _check_reserved(words, sentence)
    _register(registry, " ".join(words), "pred", len(args), sentence)
    return Predicate(_camel_case(words), args)  # type: ignore[arg-type]


def _strip_copula(tokens: list[str]) -> tuple[bool, list[str]]:
    """Strip a leading "is", then an optional "not", then an optional "a"/"an" article.
    Returns (negated, remaining predicate words) -- see the module docstring's unary-predicate
    rule: what's left is read as the predicate, "is" present or not."""
    if tokens and tokens[0] == "is":
        tokens = tokens[1:]
    negated = bool(tokens) and tokens[0] == "not"
    if negated:
        tokens = tokens[1:]
    if tokens and tokens[0] in ("a", "an"):
        tokens = tokens[1:]
    return negated, tokens


# --------------------------------------------------------------------------- quantified patterns


def _parse_every(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if not tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    subject_word, rest = tokens[0], tokens[1:]
    negated, pred_words = _strip_copula(rest)
    if not pred_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate([subject_word], (v,), registry, sentence)
    pred = _predicate(pred_words, (v,), registry, sentence)
    return ForAll(v, FolImplies(subject, FolNot(pred) if negated else pred))


def _parse_no(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if not tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    subject_word, rest = tokens[0], tokens[1:]
    negated, pred_words = _strip_copula(rest)
    if negated or not pred_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate([subject_word], (v,), registry, sentence)
    pred = _predicate(pred_words, (v,), registry, sentence)
    return ForAll(v, FolImplies(subject, FolNot(pred)))


def _parse_some(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if not tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    subject_word, rest = tokens[0], tokens[1:]
    negated, pred_words = _strip_copula(rest)
    if negated or not pred_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate([subject_word], (v,), registry, sentence)
    pred = _predicate(pred_words, (v,), registry, sentence)
    return Exists(v, FolAnd((subject, pred)))


def _parse_all_that(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if "that" not in tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    idx = tokens.index("that")
    subject_words, rest = tokens[:idx], tokens[idx + 1 :]
    if len(subject_words) != 1 or not rest:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    mid_word, after_mid = rest[0], rest[1:]
    z_words = after_mid[1:] if after_mid[:1] in (["are"], ["is"]) else after_mid
    if not z_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate(subject_words, (v,), registry, sentence)
    mid = _predicate([mid_word], (v,), registry, sentence)
    z = _predicate(z_words, (v,), registry, sentence)
    return ForAll(v, FolImplies(FolAnd((subject, mid)), z))


def _parse_quantified(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    keyword, rest = tokens[0], tokens[1:]
    if keyword == "every":
        return _parse_every(rest, registry, sentence)
    if keyword == "no":
        return _parse_no(rest, registry, sentence)
    if keyword == "some":
        return _parse_some(rest, registry, sentence)
    return _parse_all_that(rest, registry, sentence)  # keyword == "all"


# -------------------------------------------------------------------------------- ground patterns


def _parse_ground(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if len(tokens) < 2:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    c1 = _constant(tokens[0], registry, sentence)
    rest = tokens[1:]
    if rest[0] == "is":
        negated, pred_words = _strip_copula(rest)
        if not pred_words:
            raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
        pred = _predicate(pred_words, (c1,), registry, sentence)
        return FolNot(pred) if negated else pred
    return _parse_relation(c1, rest, registry, sentence)


def _parse_relation(c1: Constant, rest: list[str], registry: Registry, sentence: str) -> FolFormula:
    if len(rest) < 2:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    verb, name2, tail = rest[0], rest[1], rest[2:]
    c2 = _constant(name2, registry, sentence)
    if not tail:
        return _predicate([verb], (c1, c2), registry, sentence)
    if len(tail) != 2 or tail[0] != "and":
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    c3 = _constant(tail[1], registry, sentence)
    rel1 = _predicate([verb], (c1, c2), registry, sentence)
    rel2 = _predicate([verb], (c1, c3), registry, sentence)
    return FolAnd((rel1, rel2))


# ----------------------------------------------------------------------------------- wh-patterns


def _parse_if_copula(
    left: list[str], right: list[str], registry: Registry, sentence: str
) -> FolFormula:
    v = Variable("x")
    _, y_words = _strip_copula(left[1:])
    _, z_words = _strip_copula(right[1:])
    if not y_words or not z_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    y = _predicate(y_words, (v,), registry, sentence)
    z = _predicate(z_words, (v,), registry, sentence)
    return ForAll(v, FolImplies(y, z))


def _parse_if_relation(
    left: list[str], right: list[str], registry: Registry, sentence: str
) -> FolFormula:
    c1, c2 = _constant(left[0], registry, sentence), _constant(left[2], registry, sentence)
    c3, c4 = _constant(right[0], registry, sentence), _constant(right[2], registry, sentence)
    r1 = _predicate([left[1]], (c1, c2), registry, sentence)
    r2 = _predicate([right[1]], (c3, c4), registry, sentence)
    return FolImplies(r1, r2)


def _parse_if(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    if "then" not in tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    idx = tokens.index("then")
    left, right = tokens[:idx], tokens[idx + 1 :]
    if not left or not right:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    if len(left) >= 2 and len(right) >= 2 and left[1] == right[1] == "is" and left[0] == right[0]:
        return _parse_if_copula(left, right, registry, sentence)
    if len(left) == 3 and len(right) == 3 and left[1] != "is" and right[1] != "is":
        return _parse_if_relation(left, right, registry, sentence)
    raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)


# ------------------------------------------------------------------------------------- dispatcher


def _contains_marker(tokens: list[str], marker: tuple[str, ...]) -> bool:
    n = len(marker)
    return any(tuple(tokens[i : i + n]) == marker for i in range(len(tokens) - n + 1))


def parse(sentence: str, registry: Registry | None = None) -> FolFormula:
    """Parse one sentence into a FolFormula, or raise FolParseError.

    `registry` is shared across every sentence of one paragraph by the caller (core.session,
    Phase 8), so the two cross-sentence checks (FOL_AMBIGUOUS_INDIVIDUAL,
    FOL_UNSUPPORTED_ARITY's arity half) see every name and predicate used so far. A fresh,
    isolated call -- no registry passed -- simply cannot detect a conflict with a DIFFERENT
    sentence, which is correct: there is no other sentence for it to conflict with yet.
    """
    registry = {} if registry is None else registry
    tokens = _tokenize(sentence)
    if len(tokens) > MAX_SENTENCE_WORDS:
        raise FolParseError(FolErrorCode.FOL_SENTENCE_TOO_LONG, sentence)
    if any(_contains_marker(tokens, marker) for marker in _EQUALITY_MARKERS):
        raise FolParseError(FolErrorCode.FOL_UNSUPPORTED_ARITY, sentence, "equality")
    if not tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)

    if tokens[0] in _QUANTIFIERS:
        return _parse_quantified(tokens, registry, sentence)
    if tokens[0] == "if":
        return _parse_if(tokens[1:], registry, sentence)
    return _parse_ground(tokens, registry, sentence)


# --------------------------------------------------------------------------------- mode detection


def is_fol_formula(f: FolFormula) -> bool:
    """True if `f` contains any ForAll/Exists -- the only FOL signal this grammar can give
    without guessing.

    HLD section 18.7 originally also triggered on any Predicate with one or more arguments
    ("Alice likes Bob" alone, no quantifier). Implementing that revealed it is not a reliable
    signal at all: "We get wet" parses, by the exact same ground-relational pattern, into the
    equally well-formed Get(we, wet) -- this grammar deliberately parses by sentence POSITION,
    never by capitalization (section 18.2's own choice, to avoid guessing from a signal that
    does not reliably distinguish a name from an ordinary word). An arity>0 predicate is
    therefore just as likely to be an ordinary propositional sentence as a FOL one, and nothing
    in HLD section 18.9's worked examples needs it: every one that requires FOL mode has a
    quantifier in at least one premise. A quantifier word, by contrast, is unambiguous -- it is
    also exactly what core.english's QUANTIFIER_UNSUPPORTED refuses, so its presence can never
    legitimately mean "propositional"."""
    match f:
        case Predicate():
            return False
        case FolNot(body):
            return is_fol_formula(body)
        case FolAnd(items) | FolOr(items):
            return any(is_fol_formula(item) for item in items)
        case FolImplies(antecedent, consequent) | FolIff(antecedent, consequent):
            return is_fol_formula(antecedent) or is_fol_formula(consequent)
        case ForAll() | Exists():
            return True
    raise TypeError(f"not a FOL formula node: {f!r}")


def is_fol_sentence(sentence: str) -> bool:
    """True if `sentence` would need FOL mode. A sentence this grammar cannot parse at all is
    NOT a FOL signal -- it is core.english's problem to refuse or accept, same as today."""
    try:
        formula = parse(sentence)
    except FolParseError:
        return False
    return is_fol_formula(formula)


def detect_mode(sentences: list[str]) -> str:
    """ "fol" if any sentence needs FOL mode, else "prop" (HLD section 18.7, Phase 8 scope: this
    function exists and is callable; `session.py`'s pipeline does not yet act on its result --
    see HLD section 18.7's Phase 8b note for the deferred, separately-gated remainder)."""
    return "fol" if any(is_fol_sentence(s) for s in sentences) else "prop"
