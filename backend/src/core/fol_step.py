"""Validating a student's OWN first-order resolution step (HLD section 18.16.2).

The propositional engine's `core.logic.diagnose` cannot be reused: it is built on string literals
with no terms, no variables and no unification, and every mistake this module must name is about
exactly those things.

CONTRACT.
  FolStepError: NOT_COMPLEMENTARY | NO_UNIFIER | DOUBLE_RESOLVE | SUBST_INCOMPLETE |
                WRONG_RESOLVENT.
  check_fol_step(a, b, typed) -> FolStepError | None

THE ONE INVARIANT THIS MODULE MUST NOT BREAK: it returns None for exactly the clauses
`core.fol_resolve.resolve` produces, and for no others. Legality is decided by `resolve` itself,
never by a second implementation of the resolution rule here -- two implementations would
eventually disagree, and the one a student is graded against would be the wrong one. A validator
that accepts an unsound step teaches the student that the step is sound, which is worse than
having no validator at all.

The pivot enumeration below is for DIAGNOSIS only -- deciding WHICH mistake was made once
`resolve` has already said the step is not legal. It never decides legality.
"""

import re
from enum import Enum
from itertools import combinations

from src.core.fol_models import FolClause, FolLiteral, Substitution
from src.core.fol_resolve import apply_literal_subst, resolve
from src.core.unify import compose, unify_literals

# (literal from a, literal from b, the MGU that unifies them)
_Pivot = tuple[FolLiteral, FolLiteral, Substitution]


RawLiteral = tuple[bool, str, tuple[str, ...]]  # (negated, predicate name, raw term tokens)


class FolAnswerSyntaxError(Exception):
    """A student's typed literal is not this board's formal clause notation.

    Carries the offending text verbatim (no partial-parse guess) for the API edge to report. This
    is a SYNTAX error only -- a well-formed literal that names the wrong predicate or the wrong
    arity is not rejected here; it surfaces honestly through `check_fol_step` as
    NOT_COMPLEMENTARY or WRONG_RESOLVENT instead, which keeps this parser's job to one thing.
    """

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


# ¬Pred(term, term, ...) or ¬Pred (zero-arity, the propositional bridge). Whitespace is stripped
# before this ever runs (same convention as core.logic.normalize_literal), so none is allowed
# here -- its presence after stripping would mean it was INSIDE a name, which is not a name.
_TERM = r"[A-Za-z][A-Za-z0-9_]*"
_LITERAL = re.compile(r"^(?P<neg>[¬~]?)(?P<name>[A-Za-z][A-Za-z0-9]*)(?:\((?P<args>.*)\))?$")
_TERM_ONLY = re.compile(rf"^{_TERM}$")


def parse_literal_text(text: str) -> RawLiteral:
    """One literal in formal clause notation -> (negated, predicate name, raw term tokens).

    Terms are returned as RAW STRINGS, not yet Variable or Constant -- classifying a term needs
    the clause's own per-clause display naming (`app.render._clause_variable_names`), which
    core_fol does not own (HLD section 18.14.2: structure here, labels in render.py). The caller
    does that classification; this function only accepts or refuses the shape of the text.
    """
    stripped = "".join(text.split())
    match = _LITERAL.match(stripped)
    if match is None:
        raise FolAnswerSyntaxError(text)
    name = match.group("name")
    raw_args = match.group("args")
    if raw_args is None:
        return (bool(match.group("neg")), name, ())
    terms = raw_args.split(",")
    if any(not _TERM_ONLY.match(term) for term in terms):
        raise FolAnswerSyntaxError(text)
    return (bool(match.group("neg")), name, tuple(terms))


def parse_clause_text(text: str) -> tuple[RawLiteral, ...]:
    """The student's whole typed answer -> one raw literal per `∨`-separated piece.

    Blank (after stripping) is the empty clause, zero literals -- the same convention the
    propositional board already uses: its "insert empty clause" button just clears the field,
    sent as an empty list. One malformed literal fails the WHOLE clause; which half the student
    meant is never guessed at.
    """
    # `.split()` with no separator both tests for blank input and avoids a bare `.strip()` call
    # (core.logic/core.facts/core.english/core.fol_english own text normalization; every other
    # core module routes through them rather than handling text itself, test_normalisation.py).
    # Splitting on "∨" below needs no separate strip -- `parse_literal_text` strips each piece.
    if not text.split():
        return ()
    return tuple(parse_literal_text(piece) for piece in text.split("∨"))


class FolStepError(Enum):
    FOL_STEP_NOT_COMPLEMENTARY = "FOL_STEP_NOT_COMPLEMENTARY"
    FOL_STEP_NO_UNIFIER = "FOL_STEP_NO_UNIFIER"
    FOL_STEP_DOUBLE_RESOLVE = "FOL_STEP_DOUBLE_RESOLVE"
    FOL_STEP_SUBST_INCOMPLETE = "FOL_STEP_SUBST_INCOMPLETE"
    FOL_STEP_WRONG_RESOLVENT = "FOL_STEP_WRONG_RESOLVENT"


def _candidate_pairs(a: FolClause, b: FolClause) -> list[tuple[FolLiteral, FolLiteral]]:
    """Literal pairs a student could plausibly have resolved on: opposite polarity AND the same
    predicate name and arity. Opposite polarity alone is not enough -- `P(x)` against `¬Q(x)` has
    no predicate in common, so there is nothing a unifier could even be asked about."""
    return [
        (la, lb)
        for la in a
        for lb in b
        if la[0] != lb[0] and la[1].name == lb[1].name and len(la[1].args) == len(lb[1].args)
    ]


def _unifiable(a: FolClause, b: FolClause) -> list[_Pivot]:
    pairs = ((la, lb, unify_literals(la, lb)) for la, lb in _candidate_pairs(a, b))
    return [(la, lb, mgu) for la, lb, mgu in pairs if mgu is not None]


def _survivors(a: FolClause, b: FolClause, removed: set[FolLiteral]) -> set[FolLiteral]:
    return (set(a) | set(b)) - removed


def _double_resolvents(a: FolClause, b: FolClause, pivots: list[_Pivot]) -> set[FolClause]:
    """What the student would get by cancelling TWO complementary pairs in one step.

    Unsound -- resolution cancels one pair per step -- and the single most common way to get a
    clause that looks plausible. Computed here rather than inferred from the legal resolvents
    because a double resolution often has NO legal counterpart: cancelling either pair alone can
    leave a tautology, which `resolve` filters, so the legal set is empty while the student's
    answer still looks like an ordinary clause.
    """
    found = set()
    for (la1, lb1, mgu1), (la2, lb2, mgu2) in combinations(pivots, 2):
        if la1 == la2 or lb1 == lb2:
            continue  # the same literal cannot be cancelled twice
        merged = compose(mgu1, mgu2)
        rest = _survivors(a, b, {la1, lb1, la2, lb2})
        found.add(frozenset(apply_literal_subst(lit, merged) for lit in rest))
    return found


def _unsubstituted(a: FolClause, b: FolClause, pivots: list[_Pivot]) -> set[FolClause]:
    """The surviving literals with the MGU applied to NONE of them -- HLD section 18.5's stated
    unsoundness, where the substitution is applied only where the clauses were resolved. Empty
    when every pivot is ground, because then there is nothing to substitute and this diagnosis
    cannot honestly apply."""
    return {frozenset(_survivors(a, b, {la, lb})) for la, lb, mgu in pivots if mgu}


def check_fol_step(a: FolClause, b: FolClause, typed: FolClause) -> FolStepError | None:
    """`None` if `typed` is a legal resolvent of `a` and `b`; otherwise the most specific name
    for what went wrong (HLD section 18.16.2's diagnosis order).

    `FOL_STEP_WRONG_RESOLVENT` is the honest fallback: a legal step exists and this is not one of
    them. It is never a guess at what the student meant.
    """
    if typed in {resolvent for resolvent, _mgu in resolve(a, b)}:
        return None
    if not _candidate_pairs(a, b):
        return FolStepError.FOL_STEP_NOT_COMPLEMENTARY
    pivots = _unifiable(a, b)
    if not pivots:
        return FolStepError.FOL_STEP_NO_UNIFIER
    if typed in _double_resolvents(a, b, pivots):
        return FolStepError.FOL_STEP_DOUBLE_RESOLVE
    if typed in _unsubstituted(a, b, pivots):
        return FolStepError.FOL_STEP_SUBST_INCOMPLETE
    return FolStepError.FOL_STEP_WRONG_RESOLVENT
