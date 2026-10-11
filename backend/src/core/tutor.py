"""Tutoring POLICY: transitions, evidence, hints, selection (docs/HLD.md 7, 9, 6.6.1).

It owns no arithmetic and no `State`. The BKT update lives in `bkt.py`, the diagnosis in
`logic.py`, the search in `search.py`, the wording in `messages.yaml`, and every edit to a session
in `session.py`. What lives here is what the student's action MEANS and what happens next -- pure
functions over plain data, which is why none of it needs a session to be tested.

Two design choices are worth stating because each was the alternative to something worse.

**The transition table is CODE, not data** (v2.10 item 2). The evidence table is a pure lookup and
became `data/policy.yaml`; transitions decide what may happen next and raise named errors, which
is behaviour a reader must see.

**`search` is never called when the conclusion does not follow** (V-2, section 6.6). The empty
clause is unreachable there, so BFS would exhaust the space to the whole work budget on every
hint request. Entailment is already settled by truth table before the Prove stage, so this module
simply knows -- and `test_v2_no_search_call_at_all_when_the_conclusion_does_not_follow` counts the
calls rather than trusting the code to be read correctly.
"""

from dataclasses import dataclass

from src.core import config, search
from src.core.bkt import BktParams, update
from src.core.entail import Verdict
from src.core.logic import Clause, Code, canonical
from src.core.models import Exercise, Skill

Policy = dict[str, dict[str, str | None]]


class TransitionError(ValueError):
    """Raised when an action is not available in the current stage (HLD section 8 -> HTTP 400)."""


# ----------------------------------------------------------------- 2. transitions (code, not data)

STAGES = ("read", "facts", "translate", "prove", "explain")
ACTIONS = ("parse", "merge", "confirm", "translate", "step", "hint", "claim_not_provable")

# (stage, action) -> the stage afterwards. Total by construction: a pair that is absent is a
# TransitionError, never a silent pass, so a client that posts the wrong action in the wrong stage
# gets a named refusal instead of a half-applied state.
#
# ("prove", "merge") rewinds to "facts" on purpose -- that IS the v2.7 A4 reset, and routing it
# through the same table is what stops it being a special case somebody forgets.
TRANSITIONS: dict[tuple[str, str], str] = {
    ("read", "parse"): "facts",
    ("facts", "merge"): "facts",
    ("facts", "confirm"): "prove",
    ("translate", "translate"): "translate",
    ("translate", "confirm"): "prove",
    ("prove", "step"): "prove",
    ("prove", "hint"): "prove",
    ("prove", "claim_not_provable"): "prove",
    ("prove", "merge"): "facts",
    ("explain", "parse"): "read",
}


def allowed(stage: str) -> tuple[str, ...]:
    """The actions available in `stage`, canonically ordered."""
    return tuple(sorted(action for (owner, action) in TRANSITIONS if owner == stage))


def advance(stage: str, action: str) -> str:
    """The stage after `action`, or raise `TransitionError` naming both."""
    if (stage, action) not in TRANSITIONS:
        raise TransitionError(f"{action!r} is not available in stage {stage!r}")
    return TRANSITIONS[stage, action]


# ------------------------------------------------------------------- 3. evidence (section 9)


def step_trigger(code: Code, productive: bool | None) -> str:
    """The policy row a diagnosed step maps to.

    VALID splits three ways on productivity. `None` is the work-budget case: STRATEGY is
    genuinely unobserved there and must never be guessed wrong (section 6.6).
    """
    if code is not Code.VALID:
        return f"step.{code.value}"
    split = "unknown" if productive is None else ("productive" if productive else "unproductive")
    return f"step.VALID.{split}"


def observe(trigger: str, hinted: bool, policy: Policy) -> dict[Skill, bool]:
    """Which skills this action observed, and whether each was right. `null` rows are omitted.

    Omitted rather than present-with-a-value: `null` means NO UPDATE, so a skill that appeared
    here with any value at all would be a skill the caller then moves.

    The hint rule is a uniform TRANSFORM, not extra rows (section 9): an observed skill becomes
    wrong, and a null stays null -- a hint must never create an observation that was not already
    there, or asking for help would score skills the action never tested.
    """
    row = policy[trigger]
    return {
        Skill(name): (value == "right" and not hinted)
        for name, value in sorted(row.items())
        if value is not None
    }


def apply_evidence(
    mastery: dict[Skill, float], trigger: str, hinted: bool, policy: Policy, params: BktParams
) -> dict[Skill, float]:
    """A NEW mastery map with the observed skills updated. Never mutates its argument.

    Skills absent from `mastery` are ignored rather than added: M1 tracks three skills, and a
    TRANSLATE row that added a fourth would make `is_done` require a skill the milestone does not
    teach.
    """
    observed = observe(trigger, hinted, policy)
    return {
        skill: update(value, observed[skill], params) if skill in observed else value
        for skill, value in mastery.items()
    }


# -------------------------------------------------------------- 4. hints (V-2, the two ladders)


@dataclass(frozen=True)
class Hint:
    """A hint, carrying only what its level has earned.

    The reveal is enforced by what this object HOLDS, not by what the frontend chooses to render:
    a payload that carried the resolvent at level 1 would leak the answer to anyone with the
    developer console open, however careful the UI was.
    """

    code: str
    level: int
    clauses: tuple[Clause, ...] = ()
    resolvent: Clause | None = None

    @property
    def reveals_the_answer(self) -> bool:
        """True only at level 3, which hands over the step. Priced by the BKT hint rule."""
        return self.resolvent is not None or self.code == "HINT_NOT_FOLLOW_3"


def plan_hint(clauses: frozenset[Clause], verdict: Verdict, level: int) -> Hint:
    """The next hint, escalating with `level`.

    When the conclusion does not follow there is nothing to find, so the ladder redirects the
    student toward the right action (section 6.6.1) and **no search runs at all** -- V-2.
    """
    if level not in (1, 2, 3):
        raise ValueError(f"hint level must be 1, 2 or 3, got {level}")
    if verdict is not Verdict.ENTAILED:
        return Hint(f"HINT_NOT_FOLLOW_{level}", level)
    if search.EMPTY_CLAUSE in clauses:
        return Hint("HINT_UNAVAILABLE", level)

    # ONE allowance for the whole hint, shared by every probe `best_next_step` makes: with a
    # fresh budget per candidate this cost |candidates| x the worst single search (v2.9 A3).
    work = search.Work(config.MAX_SEARCH_WORK)
    searched = search.best_next_step(clauses, work)
    # No HINT_UNAVAILABLE branch here, and none is reachable: an ENTAILED, unsolved clause set has
    # a refutation, so it has at least one legal step. If the caller passes a verdict the board
    # contradicts, `search` raises GoalUnreachableError -- which is the honest answer, and is why
    # V-2's precondition is load-bearing rather than decorative.
    a, b, resolvent = searched or search.fallback_step(clauses)
    parents = tuple(sorted((a, b), key=canonical))
    return Hint(
        f"HINT_{level}" if searched else "HINT_FALLBACK",
        level,
        parents if level == 3 else parents[:level],
        resolvent if level == 3 else None,
    )


# ------------------------------------------------------- 6. selection (section 9 bands)

# Proof length -> band, easiest first. The ORDER is the tie-break: "nearest band, ties toward the
# easier" is distance in this tuple, and a reordering would silently invert the rule.
BANDS = ("short", "medium", "long")


def band_of_mastery(mastery: dict[Skill, float]) -> str:
    """The band to draw from: mean <0.4 short, 0.4-0.8 medium, >0.8 long (section 9)."""
    mean = sum(mastery.values()) / len(mastery) if mastery else 0.0
    if mean < 0.4:
        return "short"
    return "medium" if mean <= 0.8 else "long"


def next_exercise(
    exercises: tuple[Exercise, ...],
    bands: dict[str, str],
    mastery: dict[Skill, float],
    done_ids: tuple[str, ...],
) -> Exercise | None:
    """The exercise to offer next, or None only when the bank is empty (section 9).

    Unseen exercises first, by band distance then ID; then repeats, least-recently-seen, ties by
    lowest ID. A repeat is documented behaviour rather than an error: a student who has seen
    everything and not mastered it needs another attempt.

    `bands` arrives as plain data from `scripts/difficulty.py` via the edge -- difficulty is
    COMPUTED from the shortest proof and never hand-labelled (v2.8 A4a), and this module never
    reads a file. An exercise with no band is offered anyway rather than hidden forever.
    """
    if not exercises:
        return None
    target = BANDS.index(band_of_mastery(mastery))
    # The LAST sighting, not the first: "least recently seen" means most stale, and using the
    # first occurrence would keep re-offering whatever the student has just done.
    last_seen = {exercise_id: index for index, exercise_id in enumerate(done_ids)}

    def rank(exercise: Exercise) -> tuple[int, int, int, str]:
        band = bands.get(exercise.id)
        distance = abs(BANDS.index(band) - target) if band in BANDS else 0
        seen = exercise.id in last_seen
        return (seen, last_seen.get(exercise.id, 0) if seen else distance, distance, exercise.id)

    return min(exercises, key=rank)
