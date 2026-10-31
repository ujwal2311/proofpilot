"""FOL resolution refutation: PROVED, BUDGET_EXHAUSTED, or INCONSISTENT -- never "not provable".

See docs/HLD.md section 18.6. This module owns the proof procedure only -- clausification is
core.fol_cnf's job, resolving one pair is core.fol_resolve's. It reads no files.

CONTRACT.
  FolProofOutcome: PROVED | BUDGET_EXHAUSTED | INCONSISTENT.
  FolSearchResult: outcome, proof_steps (a, b, resolvent) triples in derivation order, clauses.
  fol_prove(premises, conclusion, budget=None) -> FolSearchResult.

THE ONE THING THIS MODULE MUST NEVER DO: report BUDGET_EXHAUSTED as "not provable". FOL is only
semi-decidable -- if the argument is valid, resolution eventually finds a refutation given
unlimited budget; if it is not, the search may never terminate. Exhausting the search SPACE
(no new resolvents left to generate) and exhausting the WORK BUDGET are therefore reported as the
exact same outcome here, not two different ones (HLD section 18.6, "NOT GoalUnreachableError" --
unlike core.search, which can prove a propositional goal unreachable because a truth table
already confirmed non-entailment first; FOL has no such pre-check, so this module can never
correctly claim the empty clause is unreachable, only that it was not found within budget).

ALGORITHM, deliberately the plainer of two standard options, stated so the choice is not mistaken
for an oversight: each round examines every pair in the CURRENT clause pool (mirroring
core.search's own `combinations(ordered, 2)` precedent) rather than only new-vs-old pairs (the
"given clause" optimization real provers use). The simpler form re-examines old pairs every
round and so spends Work less efficiently, but it is far easier to verify by hand against the
HLD section 18.9 worked examples, and the bounded grammar's small inputs make the inefficiency
immaterial -- the hand-worked 2-step proofs cost single-digit Work units either way.
"""

from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from src.core.config import MAX_FOL_SEARCH_WORK
from src.core.fol_cnf import standardize_apart_clauses, to_fol_clauses
from src.core.fol_models import FolClause, FolFormula, FolNot
from src.core.fol_resolve import canonical_clause, resolve
from src.core.search import Work

EMPTY_CLAUSE: FolClause = frozenset()
FolProofStep = tuple[FolClause, FolClause, FolClause]


class FolProofOutcome(Enum):
    PROVED = "proved"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INCONSISTENT = "inconsistent"


@dataclass
class FolSearchResult:
    outcome: FolProofOutcome
    proof_steps: list[FolProofStep]
    clauses: frozenset[FolClause]


def _clausify_all(premises: list[FolFormula], conclusion: FolFormula) -> frozenset[FolClause]:
    """Clausify every premise and the negated conclusion SEPARATELY, then standardize apart ONCE
    over their union -- see core.fol_cnf.to_fol_clauses's own docstring for why running
    standardize_apart_clauses per-formula instead would let two premises' independently-numbered
    variables collide before this function ever saw the combined set.
    """
    per_formula = [to_fol_clauses(p) for p in premises]
    per_formula.append(to_fol_clauses(FolNot(conclusion)))
    combined = frozenset().union(*per_formula) if per_formula else frozenset()
    return standardize_apart_clauses(combined)


def _resolve_round(pool: set[FolClause], work: Work) -> tuple[list[FolProofStep], FolClause | None]:
    """One level of resolution over every pair currently in `pool`.

    Returns the steps taken THIS round and, if found, the empty clause -- or None if the round
    ran out of budget or simply found nothing new. Mutates nothing; the caller decides whether to
    add the new clauses and continue.
    """
    ordered = sorted(pool, key=canonical_clause)
    steps: list[FolProofStep] = []
    for a, b in combinations(ordered, 2):
        for resolvent in sorted(resolve(a, b), key=canonical_clause):
            if not work.spend():
                return steps, None
            if resolvent in pool:
                continue
            steps.append((a, b, resolvent))
            if resolvent == EMPTY_CLAUSE:
                return steps, resolvent
    return steps, None


def _saturate(pool: set[FolClause], work: Work) -> tuple[list[FolProofStep], FolClause | None]:
    """Resolve `pool` round by round, in place, until the empty clause appears or a round adds
    nothing new (budget exhausted or genuine saturation -- see the module docstring for why
    those two are never told apart). Returns every genuine step taken and the empty clause if
    found. Shared by both phases of fol_prove so they draw on the same Work allowance.
    """
    all_steps: list[FolProofStep] = []
    while True:
        steps, found_empty = _resolve_round(pool, work)
        all_steps.extend(steps)
        new_clauses = [resolvent for *_pair, resolvent in steps if resolvent != EMPTY_CLAUSE]
        pool.update(new_clauses)
        if found_empty is not None:
            pool.add(found_empty)
            return all_steps, found_empty
        if not new_clauses:
            return all_steps, None


def fol_prove(
    premises: list[FolFormula], conclusion: FolFormula, budget: int | None = None
) -> FolSearchResult:
    """Resolution refutation: does `premises` entail `conclusion`, found within `budget` Work?

    TWO PHASES, sharing one Work allowance, because "the premises alone are contradictory" (HLD
    section 18.6, INCONSISTENT) must be checked BEFORE the negated conclusion's clauses are ever
    added -- messages.yaml's own wording is "derived from the premises before the conclusion was
    even used", which a single combined search could not tell apart from an ordinary PROVED.

    Phase 1: clausify and saturate the premises ALONE. If that alone reaches the empty clause,
    the premises contradict each other regardless of what the conclusion says -> INCONSISTENT.
    Phase 2: clausify premises + the negated conclusion TOGETHER, fresh (not continued from
    phase 1's differently-indexed pool -- core.fol_cnf.to_fol_clauses's own docstring explains
    why standardize_apart_clauses must run once over the true combined set, not twice over two
    separately-numbered ones), and saturate that. PROVED if it reaches the empty clause,
    BUDGET_EXHAUSTED otherwise.
    """
    work = Work(MAX_FOL_SEARCH_WORK if budget is None else budget)

    premise_sets = [to_fol_clauses(p) for p in premises]
    premise_union = frozenset().union(*premise_sets) if premise_sets else frozenset()
    premise_clauses = standardize_apart_clauses(premise_union)
    if EMPTY_CLAUSE in premise_clauses:
        return FolSearchResult(FolProofOutcome.INCONSISTENT, [], premise_clauses)

    premise_pool = set(premise_clauses)
    premise_steps, premises_alone_empty = _saturate(premise_pool, work)
    if premises_alone_empty is not None:
        return FolSearchResult(FolProofOutcome.INCONSISTENT, premise_steps, frozenset(premise_pool))

    pool = set(_clausify_all(premises, conclusion))
    proof_steps, found_empty = _saturate(pool, work)
    if found_empty is not None:
        return FolSearchResult(FolProofOutcome.PROVED, proof_steps, frozenset(pool))
    return FolSearchResult(FolProofOutcome.BUDGET_EXHAUSTED, proof_steps, frozenset(pool))
