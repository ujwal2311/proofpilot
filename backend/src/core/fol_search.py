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
from src.core.fol_cnf import standardize_apart_ordered, to_fol_clauses
from src.core.fol_models import FolClause, FolFormula, FolNot, Substitution
from src.core.fol_resolve import canonical_clause, resolve
from src.core.search import Work

EMPTY_CLAUSE: FolClause = frozenset()
# (left, right, resolvent, mgu). The MGU rides along because it is the marks-earning content of
# a resolution step -- "via x = socrates" -- not an implementation detail (HLD S18.15.6).
FolProofStep = tuple[FolClause, FolClause, FolClause, Substitution]
# (clause, origin) where origin is "premise" or "negated_goal". A proof trace has to show WHICH
# clause is the negated goal -- without it a reader cannot see that the refutation assumed the
# opposite of what it set out to prove (HLD S18.15.6).
FolInputClause = tuple[FolClause, str]
PREMISE, NEGATED_GOAL = "premise", "negated_goal"


class FolProofOutcome(Enum):
    PROVED = "proved"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INCONSISTENT = "inconsistent"


@dataclass
class FolSearchResult:
    outcome: FolProofOutcome
    proof_steps: list[FolProofStep]
    clauses: frozenset[FolClause]
    # Every clause the search STARTED from, in canonical order, each tagged with where it came
    # from. Not derivable from `clauses` (which also holds every resolvent) nor from
    # `proof_steps` (which omits any input the derivation never used).
    input_clauses: tuple[FolInputClause, ...] = ()


@dataclass(frozen=True)
class FolSessionResult:
    """What a FOL-mode session shows the student (HLD section 18.7, Phase 8b).

    Deliberately NOT the full clause trace: `FolSearchResult.clauses`/`proof_steps` hold
    `FolClause`/`Term` objects, which have no renderer yet (building one is its own scope, not a
    two-line add). `step_count` is enough to say "found in N steps" without one. Frozen and
    JSON-plain (an enum and an int) so it can sit on `State` and cross the API via the same
    `TypeAdapter(State)` every other core dataclass already does, no schema of its own required.
    """

    outcome: FolProofOutcome
    step_count: int

    @staticmethod
    def of(result: FolSearchResult) -> "FolSessionResult":
        return FolSessionResult(result.outcome, len(result.proof_steps))


def fol_claim_accepted(outcome: FolProofOutcome) -> bool | None:
    """Whether a "does not follow" claim is correct, from the FOL verdict alone (2026-11-01
    Facts-panel-fix follow-up: the Prove screen's claim action used to consult only the
    propositional verdict, so an argument this module had already proved valid could still score
    "does not follow" as correct).

    NEVER returns True: resolution is only semi-decidable (module docstring above), so a failed
    search is never positive evidence of non-entailment -- `None` means "do not score this",
    not "it follows". PROVED and INCONSISTENT both mean the argument is valid (INCONSISTENT
    trivially, ex falso quodlibet), so the claim is wrong either way.
    """
    return None if outcome is FolProofOutcome.BUDGET_EXHAUSTED else False


def fol_hint_code(outcome: FolProofOutcome, level: int) -> str:
    """The hint code for a FOL-mode exercise at `level` (1-3, validated at the API boundary).

    BUDGET_EXHAUSTED never varies by level: the system genuinely does not know, and an escalating
    "HINT_2"/"HINT_3" wording would imply a certainty it does not have -- same discipline as
    `fol_claim_accepted` above.
    """
    if outcome is FolProofOutcome.BUDGET_EXHAUSTED:
        return "HINT_FOL_UNKNOWN"
    return f"HINT_FOL_FOLLOWS_{level}"


def _clausify_tagged(
    premises: list[FolFormula], conclusion: FolFormula | None
) -> tuple[FolInputClause, ...]:
    """Every input clause, standardized apart, tagged premise vs negated_goal.

    Origin is decided on the PRE-renaming clause, which is why this needs
    `standardize_apart_ordered`'s pairing: after renaming, a goal clause is no longer equal to
    the clause it came from, so membership of the goal's own clause set cannot be tested.
    A clause produced by both a premise and the negated goal is tagged `premise` (first wins),
    so the tag is deterministic rather than dependent on set iteration order. Order is the one a
    worked answer uses -- premises in PARAGRAPH order, then the negated goal, canonical text
    breaking ties within a sentence -- so F1 is the first sentence's clause rather than whichever
    clause happened to sort first.

    Standardizing apart runs ONCE over the union, never per formula -- see
    core.fol_cnf.to_fol_clauses's own docstring: per-formula renaming would let two premises
    independently reuse the same variable names, undoing step 8's whole job before the combined
    set ever existed. (This function replaces the former `_clausify_all`, which returned the same
    clauses untagged.)
    """
    # `conclusion is None` is phase 1, which checks the premises ALONE -- there is no negated
    # goal to tag because none was ever added (that is what INCONSISTENT means).
    goal_side = to_fol_clauses(FolNot(conclusion)) if conclusion is not None else frozenset()
    premise_side = [to_fol_clauses(p) for p in premises]
    combined = frozenset().union(*premise_side, goal_side) if premise_side else goal_side
    # Rank each ORIGINAL clause: premises by the sentence they came from, the negated goal after
    # every premise. `setdefault` means a clause produced by two sentences keeps the earlier one.
    rank: dict[FolClause, tuple[int, int]] = {}
    for index, clauses in enumerate(premise_side):
        for clause in clauses:
            rank.setdefault(clause, (0, index))
    for clause in goal_side:
        rank.setdefault(clause, (1, len(premise_side)))
    ordered = sorted(
        standardize_apart_ordered(combined),
        key=lambda pair: (rank[pair[0]], canonical_clause(pair[1])),
    )
    return tuple(
        (renamed, PREMISE if rank[original][0] == 0 else NEGATED_GOAL)
        for original, renamed in ordered
    )


def _resolve_round(pool: set[FolClause], work: Work) -> tuple[list[FolProofStep], FolClause | None]:
    """One level of resolution over every pair currently in `pool`.

    Returns the steps taken THIS round and, if found, the empty clause -- or None if the round
    ran out of budget or simply found nothing new. Mutates nothing; the caller decides whether to
    add the new clauses and continue.
    """
    ordered = sorted(pool, key=canonical_clause)
    steps: list[FolProofStep] = []
    for a, b in combinations(ordered, 2):
        for resolvent, mgu in sorted(resolve(a, b), key=lambda pair: canonical_clause(pair[0])):
            if not work.spend():
                return steps, None
            if resolvent in pool:
                continue
            steps.append((a, b, resolvent, mgu))
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
        new_clauses = [resolvent for _a, _b, resolvent, _mgu in steps if resolvent != EMPTY_CLAUSE]
        pool.update(new_clauses)
        if found_empty is not None:
            pool.add(found_empty)
            return all_steps, found_empty
        if not new_clauses:
            return all_steps, None


def _minimal_derivation(steps: list[FolProofStep]) -> list[FolProofStep]:
    """Only the steps that actually reach the empty clause, in dependency order.

    `_saturate` returns every resolvent it generated, which is a SEARCH LOG, not a proof -- the
    Ravi worked example saturates in 22 steps where the derivation is 5, and Socrates in 3 where
    it is 2. A student reading the log learns the shape of breadth-first search, not the shape of
    resolution, so the log stays internal and only this subtree is ever returned.

    Walks back from the empty clause through each resolvent's two parents. `setdefault` keeps the
    FIRST derivation of a clause, which under round-by-round saturation is also the shallowest, so
    the extracted subtree is the shortest one the search actually found. Post-order append puts
    every dependency ahead of the step that consumes it.
    """
    parents: dict[FolClause, tuple[FolClause, FolClause, Substitution]] = {}
    for a, b, resolvent, mgu in steps:
        parents.setdefault(resolvent, (a, b, mgu))

    derivation: list[FolProofStep] = []
    collected: set[FolClause] = set()

    def walk(clause: FolClause) -> None:
        # Not in `parents` means an input clause: a leaf, nothing to derive.
        if clause in collected or clause not in parents:
            return
        collected.add(clause)
        a, b, mgu = parents[clause]
        walk(a)
        walk(b)
        derivation.append((a, b, clause, mgu))

    walk(EMPTY_CLAUSE)
    return derivation


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

    premise_inputs = _clausify_tagged(premises, None)
    premise_clauses = frozenset(clause for clause, _origin in premise_inputs)
    if EMPTY_CLAUSE in premise_clauses:
        return FolSearchResult(FolProofOutcome.INCONSISTENT, [], premise_clauses, premise_inputs)

    premise_pool = set(premise_clauses)
    premise_steps, premises_alone_empty = _saturate(premise_pool, work)
    if premises_alone_empty is not None:
        return FolSearchResult(
            FolProofOutcome.INCONSISTENT,
            _minimal_derivation(premise_steps),
            frozenset(premise_pool),
            premise_inputs,
        )

    inputs = _clausify_tagged(premises, conclusion)
    pool = {clause for clause, _origin in inputs}
    saturation_log, found_empty = _saturate(pool, work)
    if found_empty is not None:
        return FolSearchResult(
            FolProofOutcome.PROVED, _minimal_derivation(saturation_log), frozenset(pool), inputs
        )
    # No empty clause means no derivation exists to extract -- the partial log is not a proof and
    # is never presented as one (HLD section 18.6).
    return FolSearchResult(FolProofOutcome.BUDGET_EXHAUSTED, [], frozenset(pool), inputs)
