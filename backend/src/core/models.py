"""The dataclasses that cross the edge <-> core boundary (docs/HLD.md sections 4, 4.1).

They carry data and own no logic. Core never reads a file: the edge loads `exercises.json`,
`messages.yaml` and `policy.yaml` and hands the contents over as these objects (v2.4).

Everything here is FROZEN and holds tuples rather than lists, so purity is structural instead of
promised. The API replays a student's merges and actions over a stored state, so a core function
that mutated its argument would corrupt the caller's copy in silence; with a frozen dataclass the
attempt raises instead. A frozen dataclass holding a *list* would still be only shallowly
immutable -- `state.facts.append(...)` would work -- which is why the sequences are tuples.

`State` stays in core rather than moving to `api/schemas.py` (v2.10 item 1): the CLI drives core
directly, so an edge-owned State would force the CLI through the API or make it build a parallel
object of its own. The API converts to and from this type instead.

Not `types.py`: that shadows a standard-library module, and a core file silently taking
precedence over `types` is the kind of bug that costs an afternoon (v2.7 A2).
"""

from dataclasses import dataclass, field
from enum import Enum


class Skill(Enum):
    """The skills BKT tracks. Three are active in M1; TRANSLATE joins in M2.

    Declaration order is load-bearing -- the mastery display and the simulation both iterate it,
    so reordering would relabel a chart without changing a number.
    """

    CLASH = "CLASH"
    RESOLVE = "RESOLVE"
    STRATEGY = "STRATEGY"
    TRANSLATE = "TRANSLATE"


@dataclass(frozen=True)
class Exercise:
    """One bank exercise: exactly the four fields in `data/exercises.json`.

    Difficulty is deliberately absent. It is COMPUTED by `scripts/difficulty.py` from the
    shortest proof, never stored and never hand-labelled (v2.8 A4a), so there is no field here
    for a hand-written one to hide in.
    """

    id: str
    paragraph: str
    conclusion: str
    topic: str


@dataclass(frozen=True)
class Fact:
    """One proposition symbol and EVERY phrase merged into it, in first-appearance order.

    All the phrases, not just the first: the Facts screen has to show them so that an automatic
    merge stays visible and splittable (v2.6 A1). Each entry is `(phrase_id, text)` because a
    merge is expressed by phrase ID, never by raw text (v2.7 A3).
    """

    symbol: str
    phrases: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MergeChoice:
    """A user's decision about two phrases. `different` SPLITS what the stemmer merged.

    `a` and `b` are phrase IDs: a symbol cannot name one half of a group it already contains.
    """

    a: str
    b: str
    relation: str  # "same" | "opposite" | "different"


@dataclass(frozen=True)
class ClauseRec:
    """A clause on the board, with the trace the Explanation panel reads.

    `origin` distinguishes a given premise from the negated goal from a student's derivation,
    which is what lets the board explain where every clause came from.
    """

    id: str
    literals: tuple[str, ...]
    origin: str  # "given" | "goal" | "derived"
    source_sentence_id: str | None = None


@dataclass(frozen=True)
class SentenceRec:
    """One paragraph sentence and what parsing made of it.

    A failed sentence is kept with its error code rather than dropped, so the Read screen can
    show the student which sentence was refused and why (never guess, HLD section 3.4).
    """

    id: str
    text: str
    status: str  # "ok" | "error"
    error_code: str | None = None
    formula: str | None = None
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class Translation:
    """One sentence's translation attempt (M2). Empty in M1."""

    sentence_id: str
    student_formula: str | None = None
    status: str = "pending"
    diagnosis_code: str | None = None


@dataclass(frozen=True)
class State:
    """The whole session, as it crosses the boundary in both directions.

    `schema_version` is bumped on any shape change: the frontend keeps this in localStorage, and
    a stale object with a new field list would fail in the browser rather than at the boundary.

    `mastery_history` is NOT here. It was cut from M1 in v2.10 item 3 because it served only the
    stretch feature "Why this score?", and BKT needs the posterior, never the sequence that
    produced it. Re-adding it later bumps `schema_version` and leaves the BKT maths untouched.
    """

    schema_version: int
    mode: str  # "practice" | "own_question"
    exercise_id: str | None
    stage: str  # "read" | "facts" | "prove" | "explain"; M2 inserts "translate" before "prove"
    paragraph: str
    conclusion: str
    facts: tuple[Fact, ...]
    sentences: tuple[SentenceRec, ...]
    merges_applied: tuple[MergeChoice, ...]
    translations: tuple[Translation, ...]
    clauses: tuple[ClauseRec, ...]
    relevant_ids: tuple[str, ...]
    mastery: dict[Skill, float] = field(default_factory=dict)
    hint_level: int = 0
    done_ids: tuple[str, ...] = ()
    solved: bool = False
    entailment: dict | None = None
