"""Which clauses the conclusion can actually reach.

See docs/HLD.md section 6.5. Clauses are connected when they share a fact; everything reachable
from the conclusion's facts is kept, and the rest is reported to the student as "not needed for
this conclusion". Nothing is deleted from the board -- the filter shapes hints and search, and
the student may still use any clause.

The correctness argument requires the premises to be CONSISTENT: with a contradiction the
refutation can live entirely inside the unreachable component, and dropping it would destroy the
only proof. So this module takes the entailment result and refuses rather than trusting the
caller to have checked (section 7).
"""

from dataclasses import dataclass

from src.core.english import ErrorCode, ParseError
from src.core.entail import Entailment, Verdict
from src.core.logic import Clause, canonical


@dataclass(frozen=True)
class Relevance:
    kept: tuple[Clause, ...]
    dropped: tuple[Clause, ...]


def _symbols(clause: Clause) -> set[str]:
    return {literal.lstrip("~") for literal in clause}


def filter_clauses(kb_clauses, goal_clauses, entailment: Entailment) -> Relevance:
    """Split the premises into those the conclusion can reach and those it cannot.

    Reachability is transitive: a clause joins the reachable set if it shares any fact with it,
    and then contributes its own facts. Stopping at the first hop would delete the middle of
    every chain.
    """
    if entailment.verdict is Verdict.INCONSISTENT_PREMISES:
        raise ParseError(
            ErrorCode.RELEVANCE_REQUIRES_CONSISTENCY,
            "relevance filter",
            "contradiction may lie in the unreachable component",
        )

    reached = {symbol for clause in goal_clauses for symbol in _symbols(clause)}
    remaining = list(kb_clauses)
    kept: list[Clause] = []
    growing = True
    while growing:
        growing = False
        for clause in list(remaining):
            if _symbols(clause) & reached:
                remaining.remove(clause)
                kept.append(clause)
                reached |= _symbols(clause)
                growing = True

    return Relevance(tuple(sorted(kept, key=canonical)), tuple(sorted(remaining, key=canonical)))
