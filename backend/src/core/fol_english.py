"""The controlled FOL grammar: text in, FolFormula AST out.

See docs/HLD.md section 18.2. Same design principles as core.english: bounded, documented,
refused -- only the patterns listed below are parsed, anything else raises FolParseError with a
named code and no attempt to guess a meaning. No NLP library: pure token scan, same approach as
the propositional grammar, reusing its Unicode normalization (not its AST -- Predicate has typed
term arguments where Atom has a raw phrase, so the two type unions stay separate per HLD S18.1).

SUPPORTED PATTERNS (HLD section 18.2.2; the two "2026-11-02" rows are a student-authorized
extension, same bounded-grammar discipline, scoped to exactly these two forms):
  Quantified : "Every X is a Y" / "Every X is not a Y" / "Some X is a Y" / "No X is a Y" /
               "All X that|who Y are Z" /
               "Anyone|Anybody|Everyone|Everybody who Y Z" (no subject class, 2026-11-02)
  Ground     : "NAME Rs NAME" / "NAME Rs NAME and NAME" / "NAME is a Y" / "NAME is not a Y" /
               "NAME VERBs" (bare intransitive, no object, 2026-11-02) /
               "NAME VERBs the OBJECT" (verb + object phrase = one unary predicate, 2026-11-02) /
               "A or B" where A, B are each a ground pattern above (2026-11-02)
  Wh         : "If X is a Y then X is a Z" / "If NAME Rs NAME then NAME Rs NAME"

GRAMMAR LIMITATIONS, stated rather than hidden (HLD section 18.2's own out-of-scope note, plus
two more this implementation adds explicitly):
  - Predicate words ARE canonicalized for regular inflection (-s, -es, -ies), so "students"
    and "student", "study" and "studies", "pass the exam" and "passes the exam" are one symbol
    (see _canonical_word). This REVERSES the original "no stemming" limitation, which HLD
    section 18.9's own worked example disproved: without it nothing in that argument unified and
    a valid proof reported BUDGET_EXHAUSTED, which a student cannot distinguish from "no proof
    exists" -- a silent wrong answer, far worse than the merge it was avoiding. Individual NAMES
    are never canonicalized ("Socrates" is not a plural). IRREGULAR inflection is still out of
    scope and is the known gap: "person"/"people" and "child"/"children" remain two symbols,
    because no general rule reaches them and CLAUDE.md principle 1 rules out a word list.
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
  - The bare-intransitive ground form ("Ravi studies") has no negation -- "Ravi does not study"
    is refused ("not" is reserved), same as "is"/"is not" being the only negation this grammar
    ever parses. The 2026-11-02 authorization was for the positive form only.
  - "A or B" accepts at most ONE "or" per ground sentence -- a second one is refused rather than
    guessing a precedence between them, the same discipline core.english's `_junction` already
    applies to a mixed "and"/"or". Only ground sentences may appear on either side; a quantified
    clause joined by "or" is out of scope (never requested, never implemented).
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
_INDEFINITE_QUANTIFIERS = ("anyone", "anybody", "everyone", "everybody")
_RELATIVE_PRONOUNS = ("that", "who")
# "the" marks an object PHRASE rather than a second individual, which is the only signal that
# separates "Ravi passes the exam" (unary) from "Alice likes Bob" (binary). It is deliberately
# NOT reserved: it stays readable inside the predicate it helps delimit ("PassTheExam").
_DETERMINERS = ("the",)
_RESERVED = frozenset(
    {
        "every",
        "all",
        "some",
        "no",
        "and",
        "or",
        "that",
        "who",
        "if",
        "then",
        "is",
        "not",
        "a",
        "an",
        "are",
    }
    | set(_INDEFINITE_QUANTIFIERS)
)
_EQUALITY_MARKERS = (("equals",), ("is", "the", "same", "as"))


def _tokenize(sentence: str) -> list[str]:
    return [token for token in normalize_text(sentence).lower().split() if token]


# A word ending in one of these is not a regular plural -- stripping "pass" to "pas" or
# "bus" to "bu" would invent a word the writer never used.
_NEVER_STRIPPED = ("ss", "us", "is", "as", "os")


def _canonical_word(word: str) -> str:
    """Undo REGULAR English inflection so one idea is one predicate symbol.

    WHY this exists at all: without it "students"/"student" and "study"/"studies" are different
    symbols, nothing unifies, and a valid argument reports BUDGET_EXHAUSTED -- which a student
    cannot tell apart from "no proof exists" (HLD section 18.2, 2026-11-02; this replaces the
    original "no stemming" limitation, which that example proved untenable).

    Regular patterns only, never a word list (CLAUDE.md principle 1): -ies -> -y, -es after a
    sibilant, and a plain trailing -s. Irregular forms ("person"/"people", "child"/"children")
    are out of reach of any general rule and stay out of scope, stated in the module docstring
    rather than guessed at.
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 3 and word[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return word[:-2]
    if word.endswith("s") and len(word) > 3 and not word.endswith(_NEVER_STRIPPED):
        return word[:-1]
    return word


def _camel_case(words: list[str]) -> str:
    """CamelCase-join words into one predicate or relation name: ["is","taller","than"] ->
    "IsTallerThan", ["human"] -> "Human" (HLD section 18.2.3)."""
    return "".join(word.capitalize() for word in words)


def _check_reserved(words: list[str], sentence: str) -> None:
    """Refuse a name/predicate phrase that is, or contains, a structural keyword -- the guard
    that keeps a malformed sentence from being silently CamelCased into a bogus predicate (see
    the module docstring's limitations list)."""
    if any(word in _QUANTIFIERS + _INDEFINITE_QUANTIFIERS for word in words):
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
    """An individual name. The NAME is never canonicalized -- "Socrates" is not a plural of
    "Socrate" -- but the registry KEY is, so that the role clash in "Ravi studies or Studies is
    a person" is still caught now that predicates are registered under their canonical form.
    """
    _check_reserved([word], sentence)
    _register(registry, _canonical_word(word), "const", 0, sentence)
    return Constant(word)


def _predicate(
    words: list[str], args: tuple[object, ...], registry: Registry, sentence: str
) -> Predicate:
    """Build a predicate from `words`, canonicalized so inflection never splits one idea in two.

    The registry is keyed by the CANONICAL phrase, not the written one, so the cross-sentence
    arity check sees "students" and "student" as the one symbol they now produce.
    """
    _check_reserved(words, sentence)
    canonical = [_canonical_word(word) for word in words]
    _register(registry, " ".join(canonical), "pred", len(args), sentence)
    return Predicate(_camel_case(canonical), args)  # type: ignore[arg-type]


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


def _parse_simple_quantified(
    keyword: str, tokens: list[str], registry: Registry, sentence: str
) -> FolFormula:
    """ "Every X is a Y" / "Every X is not a Y" / "No X is a Y" / "Some X is a Y".

    One shape behind three keywords: a subject word, then whatever the copula leaves as the
    predicate. Only "every" accepts the negated form -- "No X is not a Y" and "Some X is not a Y"
    are undocumented variants, so they are refused rather than guessed at (HLD section 18.2).
    Written as one function because the three were character-for-character identical apart from
    the node they build, and three copies drift.
    """
    if not tokens:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    subject_word, rest = tokens[0], tokens[1:]
    negated, pred_words = _strip_copula(rest)
    if not pred_words or (negated and keyword != "every"):
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate([subject_word], (v,), registry, sentence)
    pred = _predicate(pred_words, (v,), registry, sentence)
    if keyword == "some":
        return Exists(v, FolAnd((subject, pred)))
    if negated or keyword == "no":
        return ForAll(v, FolImplies(subject, FolNot(pred)))
    return ForAll(v, FolImplies(subject, pred))


def _relative_index(tokens: list[str]) -> int:
    """Where the relative clause starts, or -1. "that" and "who" are the same connector here --
    which one the writer used carries no logical difference."""
    for index, token in enumerate(tokens):
        if token in _RELATIVE_PRONOUNS:
            return index
    return -1


def _relative_clause(rest: list[str], sentence: str) -> tuple[list[str], list[str]]:
    """The relative clause's own predicate, and whatever follows it.

    ONE bounded rule, covering both "who study" and "who is lucky": the predicate is exactly one
    word, optionally preceded by "is" and an article. Allowing more would make the split between
    the clause and the main predicate ("...who is lucky | passes the exam") a guess.
    """
    index = 0
    if rest[:1] == ["is"]:
        index = 2 if rest[1:2] in (["a"], ["an"]) else 1
    if len(rest) <= index:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    return [rest[index]], rest[index + 1 :]


def _main_predicate(after_mid: list[str], sentence: str) -> list[str]:
    """The consequent's words, with a leading copula stripped ("...are migratory")."""
    z_words = after_mid[1:] if after_mid[:1] in (["are"], ["is"]) else after_mid
    if not z_words:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    return z_words


def _parse_all_bare_svo(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    """ "All SUBJECT VERB OBJECT-PHRASE" -- no relative clause, no copula (2026-11-02). The
    object phrase must carry the SAME signal the ground verb+object pattern requires (a
    determiner, or its last word is a regular plural) -- reused, not re-derived, so the two
    patterns can never disagree about what counts as an object phrase. A quantified relation to
    a NAMED INDIVIDUAL ("All engineers like Bob") is still refused: genuinely ambiguous the same
    way the ground pattern is, never guessed at.
    """
    if len(tokens) < 3:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    subject_word, rest = tokens[0], tokens[1:]
    if rest[1] not in _DETERMINERS and _canonical_word(rest[-1]) == rest[-1]:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    v = Variable("x")
    subject = _predicate([subject_word], (v,), registry, sentence)
    verb_object = _predicate(rest, (v,), registry, sentence)
    return ForAll(v, FolImplies(subject, verb_object))


def _parse_all_that(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    idx = _relative_index(tokens)
    if idx < 0:
        return _parse_all_bare_svo(tokens, registry, sentence)
    subject_words, rest = tokens[:idx], tokens[idx + 1 :]
    if len(subject_words) != 1 or not rest:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    mid_words, after_mid = _relative_clause(rest, sentence)
    z_words = _main_predicate(after_mid, sentence)
    v = Variable("x")
    subject = _predicate(subject_words, (v,), registry, sentence)
    mid = _predicate(mid_words, (v,), registry, sentence)
    z = _predicate(z_words, (v,), registry, sentence)
    return ForAll(v, FolImplies(FolAnd((subject, mid)), z))


def _parse_indefinite(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    """ "Anyone who is lucky passes the exam" -> ForAll(x, Lucky(x) -> PassTheExam(x)).

    Same shape as "All X who Y are Z" minus the subject class: "anyone" names no category, so
    the relative clause alone is the antecedent. The relative pronoun is REQUIRED -- "anyone
    passes the exam" has no antecedent to build an implication from and is refused rather than
    read as a bare fact about an individual called "anyone".
    """
    if tokens[:1] and tokens[0] in _RELATIVE_PRONOUNS:
        mid_words, after_mid = _relative_clause(tokens[1:], sentence)
        z_words = _main_predicate(after_mid, sentence)
        v = Variable("x")
        antecedent = _predicate(mid_words, (v,), registry, sentence)
        return ForAll(v, FolImplies(antecedent, _predicate(z_words, (v,), registry, sentence)))
    raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)


def _parse_quantified(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    keyword, rest = tokens[0], tokens[1:]
    if keyword == "all":
        return _parse_all_that(rest, registry, sentence)
    return _parse_simple_quantified(keyword, rest, registry, sentence)


# -------------------------------------------------------------------------------- ground patterns


def _parse_ground(tokens: list[str], registry: Registry, sentence: str) -> FolFormula:
    """ "NAME is a Y" / "NAME is not a Y" / "NAME Rs NAME(s)" / "NAME VERBs" (bare intransitive,
    2026-11-02) / "A or B" where A and B are each one of the above (2026-11-02) -- a thin split,
    not a second grammar: each side is just this same function called again.
    """
    if tokens.count("or") > 1:
        raise FolParseError(FolErrorCode.FOL_UNKNOWN_PATTERN, sentence)
    if "or" in tokens:
        split = tokens.index("or")
        left = _parse_ground(tokens[:split], registry, sentence)
        right = _parse_ground(tokens[split + 1 :], registry, sentence)
        return FolOr((left, right))
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
    if len(rest) == 1:
        return _predicate(rest, (c1,), registry, sentence)
    if rest[1] in _DETERMINERS or _canonical_word(rest[-1]) != rest[-1]:
        # "Ravi passes the exam": a determiner marks an object PHRASE, not an individual named
        # "the" (_DETERMINERS). "Aisha solves problems" has no determiner, but its head noun is a
        # regular plural -- checked by the LAST word so a modifier ("solves hard problems") does
        # not hide it -- which a proper name essentially never is in this grammar's own worked
        # examples. Both signals route to the same unary verb+object reading; neither guesses
        # when the object is a bare, non-plural, undetermined word ("Alice likes Bob" still means
        # two individuals). KNOWN, ACCEPTED LIMITATION, same risk already taken for
        # _canonical_word itself: a proper name that happens to be a regular plural form (ending
        # in "-s" the way _canonical_word strips) would be misread the same way.
        return _predicate(rest, (c1,), registry, sentence)
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
    if tokens[0] in _INDEFINITE_QUANTIFIERS:
        return _parse_indefinite(tokens[1:], registry, sentence)
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


def _has_quantifier_word(sentence: str) -> bool:
    """True if `sentence` lexically contains a quantifier word, whether or not THIS grammar's
    narrower patterns can parse it into a formula (2026-11-02 fix, HLD S18.16.10).

    Safe by construction: `core.english`'s own grammar refuses every one of these words
    UNCONDITIONALLY (its own QUANTIFIER_UNSUPPORTED check), so this can never take a sentence
    away from propositional that propositional would otherwise have accepted -- there is no such
    sentence. Before this, a sentence this grammar could not parse at all (e.g. "All engineers
    solve problems" -- no copula, no relative clause, a genuine pattern gap) was treated as "not
    a FOL signal", so a paragraph containing it fell through to full propositional treatment --
    Facts panel, relevance banner -- none of which was ever meant to see a quantifier.
    """
    tokens = _tokenize(sentence)
    return any(token in _QUANTIFIERS or token in _INDEFINITE_QUANTIFIERS for token in tokens)


def is_fol_sentence(sentence: str) -> bool:
    """True if `sentence` would need FOL mode -- either it parses into a formula with a
    quantifier, or it lexically signals one this grammar cannot (yet) parse."""
    try:
        formula = parse(sentence)
    except FolParseError:
        return _has_quantifier_word(sentence)
    return is_fol_formula(formula)


def detect_mode(sentences: list[str]) -> str:
    """ "fol" if any sentence needs FOL mode, else "prop" (HLD section 18.7, Phase 8 scope: this
    function exists and is callable; `session.py`'s pipeline does not yet act on its result --
    see HLD section 18.7's Phase 8b note for the deferred, separately-gated remainder)."""
    return "fol" if any(is_fol_sentence(s) for s in sentences) else "prop"


# ----------------------------------------------------------------------- display (Facts panel)


# Binding tightness, loosest first: ↔ < → < ∨ < ∧ < ¬ < atoms. A child LOOSER than its parent
# must be parenthesized or the text says something the tree does not -- "¬A ∧ B" read back is
# (¬A) ∧ B, not ¬(A ∧ B). A child at least as tight needs nothing, so the conventional
# "A ∧ B → C" keeps its conventional shape instead of drowning in brackets.
_LOOSEST = 0
_PRECEDENCE: dict[type, int] = {
    FolIff: _LOOSEST,
    FolImplies: 1,
    FolOr: 2,
    FolAnd: 3,
    FolNot: 4,
}
_ATOMIC = 5  # predicates, and quantifiers (which bracket their own body)


def _precedence(f: FolFormula) -> int:
    return _PRECEDENCE.get(type(f), _ATOMIC)


def _grouped(child: FolFormula, parent: int) -> str:
    """`child` rendered, bracketed only when it binds LOOSER than the parent it sits inside."""
    text = render(child)
    return f"({text})" if _precedence(child) < parent else text


def display_term_name(name: str) -> str:
    """A Skolem term's name in the notation a logic course uses: sk_c0 -> C1, sk_f0 -> f1.

    `core.fol_cnf` numbers Skolem terms from an internal counter, and those internal names are
    part of clause identity -- renaming them there would change what unifies with what. This is
    display only, the same treatment the pipeline's `c2_v0` variable names already get: a student
    reading "sk_f0(x)" learns nothing from the prefix, and every textbook writes f1(x).
    """
    for prefix, shown in (("sk_c", "C"), ("sk_f", "f")):
        suffix = name[len(prefix) :]
        if name.startswith(prefix) and suffix.isdigit():
            return f"{shown}{int(suffix) + 1}"
    return name


def _term_text(term: object) -> str:
    """A term as text: a name, or `f(arg, ...)` for a function term, recursively."""
    args = getattr(term, "args", None)
    if args:
        inner = ", ".join(_term_text(a) for a in args)
        return f"{display_term_name(term.name)}({inner})"  # type: ignore[attr-defined]
    return display_term_name(term.name)  # type: ignore[attr-defined]


def render(f: FolFormula) -> str:
    """The reading `parse()` built from one sentence, in the symbols a logic course already
    uses -- shown back to the student instead of core.english's refusal (HLD section 18.7's
    Facts-panel fix: a sentence FOL understood must never be reported as propositionally wrong).
    `parse()` never produces a `FunctionTerm`, but the CNF working display (HLD S18.15.6) hands
    this POST-Skolemization formulas, which do -- so terms are rendered recursively via
    `_term_text`. Printing a `FunctionTerm`'s bare `.name` would drop the arguments that are the
    whole difference between a Skolem function and a Skolem constant.
    """
    match f:
        case Predicate(name, args):
            return f"{name}({', '.join(_term_text(a) for a in args)})" if args else name
        case FolNot(body):
            return f"¬{_grouped(body, _PRECEDENCE[FolNot])}"
        case FolAnd(items):
            return " ∧ ".join(_grouped(item, _PRECEDENCE[FolAnd]) for item in items)
        case FolOr(items):
            return " ∨ ".join(_grouped(item, _PRECEDENCE[FolOr]) for item in items)
        case FolImplies(antecedent, consequent):
            level = _PRECEDENCE[FolImplies]
            return f"{_grouped(antecedent, level)} → {_grouped(consequent, level)}"
        case FolIff(left, right):
            level = _PRECEDENCE[FolIff]
            return f"{_grouped(left, level)} ↔ {_grouped(right, level)}"
        case ForAll(var, body):
            return f"∀{var.name} ({render(body)})"
        case Exists(var, body):
            return f"∃{var.name} ({render(body)})"
    raise TypeError(f"not a FOL formula node: {f!r}")


def display_readings(sentence_texts: list[str]) -> list[str | None]:
    """Each sentence's FOL reading, rendered, or `None` if it does not parse alone -- used ONLY
    so `core.session` can decide which grammar's refusal (if either) a sentence shows on the
    Facts screen. One registry shared across every sentence, same cross-sentence contract as
    `parse()`, but continuing past a failure instead of raising -- display must still cover
    sentence 3 even when sentence 1 was refused.
    """
    registry: Registry = {}
    readings: list[str | None] = []
    for text in sentence_texts:
        try:
            readings.append(render(parse(text, registry)))
        except FolParseError:
            readings.append(None)
    return readings
