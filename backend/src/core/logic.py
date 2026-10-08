"""Propositional resolution and step diagnosis.

See docs/HLD.md section 6.7. This module owns literal normalization, single-pivot resolution,
and naming the student's mistake. It owns neither search nor CNF conversion, and it reads no
files -- every input arrives as a literal or a clause.
"""

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations

Literal = str
Clause = frozenset[Literal]

# The two negation markers a student may type. "~" is canonical because it survives every
# encoding and keyboard; "¬" is accepted because it is what textbooks print.
_ASCII_NOT = "~"
_UNICODE_NOT = "¬"


def normalize_literal(raw: str) -> Literal:
    """Return the canonical form of one literal, or raise ValueError.

    Accepts "P", "p", "~P", "¬P" and any internal or surrounding whitespace. Rejects
    everything else -- including "~~P". Collapsing a double negation would be a guess about
    what the student meant, and this project never guesses (CLAUDE.md principle 2).
    """
    if not isinstance(raw, str):
        raise ValueError(f"literal must be a string, got {type(raw).__name__}")

    # Strip all whitespace, not just the ends, so " ~ p " normalizes without a separate case.
    text = "".join(raw.split()).replace(_UNICODE_NOT, _ASCII_NOT)

    negated = text.startswith(_ASCII_NOT)
    symbol = text[1:] if negated else text

    if len(symbol) != 1 or not symbol.isalpha() or not symbol.isascii():
        raise ValueError(
            f"{raw!r} is not a literal: expected a single letter, optionally preceded by one "
            f"'{_ASCII_NOT}' or '{_UNICODE_NOT}' (for example 'P' or '{_ASCII_NOT}P')"
        )

    return f"{_ASCII_NOT}{symbol.upper()}" if negated else symbol.upper()


def negate(literal: Literal) -> Literal:
    """Flip a canonical literal's polarity."""
    return literal[1:] if literal.startswith(_ASCII_NOT) else f"{_ASCII_NOT}{literal}"


def canonical(clause: Clause) -> tuple[Literal, ...]:
    """Order-independent key for a clause.

    Every comparison, tie-break and display path goes through this. Iterating a frozenset
    directly would expose Python's per-process hash randomization and make hints and test
    results differ between runs (docs/HLD.md section 17.10).
    """
    return tuple(sorted(clause))


def is_tautology(clause: Clause) -> bool:
    """True if the clause contains both a literal and its negation."""
    return any(negate(literal) in clause for literal in clause)


def _pivots(a: Clause, b: Clause) -> tuple[Literal, ...]:
    """Literals of `a` whose negation appears in `b`, in canonical order."""
    return tuple(sorted(literal for literal in a if negate(literal) in b))


def resolvents(a: Clause, b: Clause) -> frozenset[Clause]:
    """Every clause obtainable by resolving on exactly ONE complementary pair.

    Resolving on two pairs at once is unsound, which is why it is never produced here and is
    instead diagnosed as DOUBLE_CANCEL.
    """
    return frozenset((a - {pivot}) | (b - {negate(pivot)}) for pivot in _pivots(a, b))


class Code(Enum):
    """Diagnosis outcomes, in the order `diagnose` tests them."""

    NO_CLASH = "NO_CLASH"
    DOUBLE_CANCEL = "DOUBLE_CANCEL"
    WRONG_RESOLVENT = "WRONG_RESOLVENT"
    TAUTOLOGY = "TAUTOLOGY"
    DUPLICATE = "DUPLICATE"
    VALID = "VALID"


@dataclass(frozen=True)
class Diagnosis:
    """What the student's step was, and -- for WRONG_RESOLVENT -- how it differed."""

    code: Code
    missing: Clause = field(default_factory=frozenset)
    extra: Clause = field(default_factory=frozenset)


def _double_cancel_candidates(a: Clause, b: Clause, pivots: tuple[Literal, ...]) -> set[Clause]:
    """Every union of `a` and `b` with two or more complementary pairs struck out.

    "2+", not "all": a student who cancels two of three pairs has made exactly this mistake and
    deserves the same message. The pivot count is bounded by the symbol count (at most a
    handful), so enumerating subsets is cheap and exact rather than approximate.
    """
    union = a | b
    return {
        union - {literal for pivot in chosen for literal in (pivot, negate(pivot))}
        for size in range(2, len(pivots) + 1)
        for chosen in combinations(pivots, size)
    }


def _closest(claimed: Clause, candidates: frozenset[Clause]) -> Clause:
    """The candidate resolvent nearest to what the student wrote.

    When WRONG_RESOLVENT is reachable there is provably exactly one candidate (see the
    two-pivot argument in docs/HLD.md section 6.7), so this only ever picks from a single
    option. The canonical tie-break is kept anyway: it costs one term and guarantees the
    message cannot vary between runs if that argument is ever weakened.
    """
    return min(candidates, key=lambda r: (len(r ^ claimed), canonical(r)))


def diagnose(a: Clause, b: Clause, claimed: Clause, existing: frozenset[Clause]) -> Diagnosis:
    """Name the mistake in one proposed resolution step.

    `existing` is the full current clause set, parents included -- harmless, because a resolvent
    drops its pivot and so can never equal a parent that carries it.

    The order is load-bearing. Each check is the most specific explanation available at that
    point, so testing them in this sequence turns "wrong" into a usable message.
    """
    pivots = _pivots(a, b)
    if not pivots:
        return Diagnosis(Code.NO_CLASH)

    # Before calling the step wrong, check whether it is the one *specific* unsound move:
    # striking out several complementary pairs in a single step.
    if len(pivots) >= 2 and claimed in _double_cancel_candidates(a, b, pivots):
        return Diagnosis(Code.DOUBLE_CANCEL)

    produced = resolvents(a, b)
    if claimed not in produced:
        target = _closest(claimed, produced)
        return Diagnosis(Code.WRONG_RESOLVENT, missing=target - claimed, extra=claimed - target)

    # From here the step is a genuine resolvent; the remaining codes are about whether it is
    # worth adding to the board.
    if is_tautology(claimed):
        return Diagnosis(Code.TAUTOLOGY)
    if claimed in existing:
        return Diagnosis(Code.DUPLICATE)
    return Diagnosis(Code.VALID)
