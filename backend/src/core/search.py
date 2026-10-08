"""Breadth-first search for the shortest resolution refutation.

See docs/HLD.md section 6.6. A state is the current set of clauses, an action adds one new
non-tautological single-pivot resolvent, every action costs 1, and the goal is reached when the
empty clause is present. Because every action only ever *adds* a clause, BFS gives the shortest
proof and the distance can never increase -- which is what makes "productive" meaningful.

This module owns distance, productivity and which step to suggest. It owns neither diagnosis
(core.logic) nor wording (messages.yaml), and it reads no files.
"""

from itertools import combinations

from src.core.config import MAX_SEARCH_NODES
from src.core.logic import Clause, canonical, is_tautology, resolvents

State = frozenset[Clause]
Step = tuple[Clause, Clause, Clause]

EMPTY_CLAUSE: Clause = frozenset()

# distance() is a pure function of the state, so memoizing it cannot change an answer. Only
# confirmed distances are stored: a cap hit depends on max_nodes, and caching it under the state
# alone would poison a later call that has a larger budget.
_DISTANCE_CACHE: dict[State, int] = {}


class GoalUnreachableError(RuntimeError):
    """Raised when BFS exhausts the space without deriving the empty clause.

    Resolution is refutation-complete, so this can only happen when the premises do not entail
    the goal -- a case the caller is required to have settled by truth table before searching
    (docs/HLD.md sections 6.6 and 7). Returning None here instead would tell the caller "too
    hard" when the truth is "impossible", and those demand opposite responses.
    """


def clear_distance_cache() -> None:
    """Drop memoized distances. Used by tests to keep each case independent."""
    _DISTANCE_CACHE.clear()


def candidate_steps(state: State) -> list[Step]:
    """Every legal (clause, clause, resolvent) triple, in canonical order.

    The single source of expansion order for the whole module: successors(), best_next_step()
    and the search itself all read it, so there is one place where determinism can go wrong
    rather than three. Tautologies and clauses already present are skipped -- neither changes
    what is derivable, and allowing them would let the search wander through useless states.
    """
    ordered = sorted(state, key=canonical)
    steps: list[Step] = []
    for a, b in combinations(ordered, 2):
        for resolvent in sorted(resolvents(a, b), key=canonical):
            if resolvent not in state and not is_tautology(resolvent):
                steps.append((a, b, resolvent))
    return steps


def successors(state: State) -> list[State]:
    """Every state reachable by one legal step, in canonical order."""
    seen: set[Clause] = set()
    children: list[State] = []
    for _, _, resolvent in candidate_steps(state):
        if resolvent not in seen:
            seen.add(resolvent)
            children.append(state | {resolvent})
    return children


def distance(state: State, max_nodes: int = MAX_SEARCH_NODES) -> int | None:
    """Fewest steps from `state` to the empty clause, or None if the node cap was reached.

    Raises GoalUnreachableError if the space is exhausted first; see that class for why that is
    not folded into None.
    """
    if EMPTY_CLAUSE in state:
        return 0
    if state in _DISTANCE_CACHE:
        return _DISTANCE_CACHE[state]

    visited = {state}
    frontier = [state]
    depth = 0
    expanded = 0

    while frontier:
        depth += 1
        next_frontier: list[State] = []
        for current in frontier:
            for child in successors(current):
                if child in visited:
                    continue
                if EMPTY_CLAUSE in child:
                    _DISTANCE_CACHE[state] = depth
                    return depth
                visited.add(child)
                next_frontier.append(child)
            expanded += 1
            if expanded >= max_nodes:
                return None
        frontier = next_frontier

    raise GoalUnreachableError(
        "no refutation exists from this clause set; entailment must be checked before searching"
    )


def productive(before: State, after: State, max_nodes: int = MAX_SEARCH_NODES) -> bool | None:
    """Did the step shorten the proof? None when either search hit the cap.

    None is returned rather than guessed: an unknown distance makes productivity genuinely
    undecidable, and the evidence table treats that as "no observation" instead of a wrong one.
    """
    d_before = distance(before, max_nodes)
    d_after = distance(after, max_nodes)
    if d_before is None or d_after is None:
        return None
    return d_after == d_before - 1


def best_next_step(state: State, max_nodes: int = MAX_SEARCH_NODES) -> Step | None:
    """The first step of a shortest proof, or None if there is nothing useful to suggest.

    None covers three cases that all mean the same thing to a caller: already solved, the cap was
    reached, or no candidate could be confirmed productive within budget. The caller falls back
    to fallback_step().
    """
    target = distance(state, max_nodes)
    if not target:  # already solved (0) or cap reached (None)
        return None
    for a, b, resolvent in candidate_steps(state):
        if distance(state | {resolvent}, max_nodes) == target - 1:
            return (a, b, resolvent)
    return None


def fallback_step(state: State) -> Step | None:
    """A legal step chosen by rule instead of by search, for when the cap is reached.

    Preference goes to the shortest clause available. Unit clauses are what actually drive a
    refutation towards the empty clause, so this is a cheap heuristic that is usually sensible --
    but it is not searched, and the caller must present it as a suggestion rather than the best
    move (docs/HLD.md section 6.6, "Cap fallback").
    """
    ordered = sorted(state, key=lambda clause: (len(clause), canonical(clause)))
    for a, b in combinations(ordered, 2):
        for resolvent in sorted(resolvents(a, b), key=canonical):
            if resolvent not in state and not is_tautology(resolvent):
                return (a, b, resolvent)
    return None
