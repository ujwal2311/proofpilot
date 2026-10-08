"""Does the conclusion follow? Decided by truth table, never by search.

See docs/HLD.md section 6.4. Keeping this separate from the proof search is what lets the system
know the answer before the student starts, and therefore refuse to search for a refutation that
provably does not exist (section 6.6).

Rows are enumerated as a binary counter over the symbols in sorted order, so the counterexample
is the first qualifying row and is identical on every machine and in every process. "Any
satisfying row" would make the student's feedback vary between runs.
"""

from dataclasses import dataclass
from enum import Enum

from src.core.config import MAX_FACTS
from src.core.english import ErrorCode, ParseError
from src.core.logic import Clause

Assignment = dict[str, bool]


class Verdict(Enum):
    ENTAILED = "ENTAILED"
    NOT_ENTAILED = "NOT_ENTAILED"
    INCONSISTENT_PREMISES = "INCONSISTENT_PREMISES"


@dataclass(frozen=True)
class Entailment:
    verdict: Verdict
    counterexample: Assignment | None = None
    warnings: tuple[str, ...] = ()


def symbols_of(clauses) -> tuple[str, ...]:
    """Every symbol appearing in the clauses, sorted. Sorted is what makes rows reproducible."""
    return tuple(sorted({literal.lstrip("~") for clause in clauses for literal in clause}))


def _holds(clause: Clause, row: Assignment) -> bool:
    return any(
        (not row[literal[1:]]) if literal.startswith("~") else row[literal] for literal in clause
    )


def _first_model(clauses, symbols: tuple[str, ...]) -> Assignment | None:
    """The first assignment satisfying every clause, in canonical row order, or None."""
    for counter in range(2 ** len(symbols)):
        row = {symbol: bool(counter >> index & 1) for index, symbol in enumerate(symbols)}
        if all(_holds(clause, row) for clause in clauses):
            return row
    return None


def check(kb_clauses, negated_goal_clauses) -> Entailment:
    """Decide whether the premises entail the conclusion.

    Takes the goal ALREADY NEGATED (cnf.goal_clauses), because that is the form a refutation
    needs and converting it twice would be two chances to disagree.

    Order matters. Consistency is tested first: a contradiction entails everything, so reporting
    "it follows" would be true and useless, and it is also the condition that would make the
    relevance filter unsound (section 6.5).
    """
    symbols = symbols_of([*kb_clauses, *negated_goal_clauses])
    if len(symbols) > MAX_FACTS:
        raise ParseError(
            ErrorCode.TOO_MANY_FACTS, f"{len(symbols)} symbols", "truth_table_would_exceed_cap"
        )

    if _first_model(kb_clauses, symbols) is None:
        return Entailment(Verdict.INCONSISTENT_PREMISES)

    warnings: tuple[str, ...] = ()
    if _first_model(negated_goal_clauses, symbols) is None:
        # The negation of the goal is unsatisfiable, so the goal is valid: it follows from any
        # premises at all. True, but almost never what the student meant to ask.
        warnings = ("TAUTOLOGICAL_CONCLUSION: the conclusion is true in every situation",)

    witness = _first_model([*kb_clauses, *negated_goal_clauses], symbols)
    if witness is None:
        return Entailment(Verdict.ENTAILED, None, warnings)
    return Entailment(Verdict.NOT_ENTAILED, witness, warnings)
