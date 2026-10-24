"""Session mechanics: turn a paragraph into a board, and apply one event to a `State`.

The companion to `tutor.py`, and the line between them is what each one is ABOUT:

  * `tutor.py` is POLICY -- what the student's action means, what may happen next, what to hint,
    what to offer next. Pure functions over plain data, and it never touches a `State`.
  * `session.py` is MECHANICS -- the section 7 pipeline, and every edit to a `State`.

Splitting them means `State` is written by exactly ONE module. While both lived together, the
module that decided policy also edited the session, so a change to either could reach the other.

**The pipeline is in one function** (`analyse`). The API and the CLI both drive it, so putting the
order in either edge would give two places for it to drift -- and the order is a CORRECTNESS
requirement, not a convention: entailment is vacuous from a contradiction, and the relevance
filter can delete the only refutation (section 7).

Reads no file. Every data file is loaded by an edge and handed over as plain data (v2.4).
"""

from dataclasses import dataclass, field, replace

from src.core.cnf import goal_clauses, premise_clauses
from src.core.english import ErrorCode, ParseError, parse_sentence, phrases_of, prepare
from src.core.entail import Entailment, Verdict, check
from src.core.facts import extract
from src.core.logic import Clause, canonical
from src.core.models import ClauseRec, Fact, MergeChoice, SentenceRec, Skill, State, Translation
from src.core.relevance import Relevance, filter_clauses


class ResetRequired(ValueError):
    """Raised when a merge change would discard downstream work and was not confirmed (v2.7 A4)."""


@dataclass(frozen=True)
class Analysis:
    """Everything one pass over a paragraph produces. `None` means the pass stopped earlier."""

    sentences: tuple[SentenceRec, ...]
    facts: tuple[Fact, ...]
    kb: tuple[Clause, ...]
    goal: tuple[Clause, ...]
    entailment: Entailment | None
    relevance: Relevance | None
    warnings: tuple[str, ...]
    # Which SENTENCE each premise clause came from, so the Explanation panel can say where a
    # clause on the board came from (`ClauseRec.source_sentence_id`, section 4). Keyed by clause
    # rather than parallel to `kb`, because positional parallelism between two tuples is the kind
    # of invariant that breaks silently. A clause two sentences both produce keeps the FIRST.
    source_of: dict[Clause, str] = field(default_factory=dict)


def _one(conclusion: str) -> list[str]:
    """The conclusion, normalized by the same splitter the paragraph uses. Exactly one sentence.

    Two sentences in the conclusion box is a refusal rather than a guess about which one is the
    claim -- picking the first would quietly prove something the student did not ask about.
    """
    found = prepare(conclusion)
    if len(found) != 1:
        raise ParseError(ErrorCode.UNPARSEABLE, conclusion, "conclusion_must_be_one_sentence")
    return found


def analyse(paragraph: str, conclusion: str, merges: tuple[MergeChoice, ...] = ()) -> Analysis:
    """Run the section 7 ordering once. The conclusion is the LAST sentence record.

    A sentence that fails to parse is kept with its error code rather than dropped, so the Read
    screen can show which sentence was refused and why -- and the others still parse. A paragraph
    is a list of attempts, not a transaction.
    """
    records: list[SentenceRec] = []
    trees: list[object] = []
    # The conclusion goes through the SAME splitter as the paragraph. Passing it raw left its
    # trailing full stop attached, so "we get wet." and "we get wet" became two different facts
    # and the rain example stopped entailing -- a silent wrong answer, not a crash.
    for index, text in enumerate([*prepare(paragraph), *_one(conclusion)], start=1):
        try:
            trees.append(parse_sentence(text))
            records.append(SentenceRec(f"s{index}", text, "ok"))
        except ParseError as refused:
            trees.append(None)
            records.append(SentenceRec(f"s{index}", text, "error", refused.code.value))

    if trees[-1] is None:
        # Nothing to decide the paragraph against, and inventing a verdict would be a guess.
        return Analysis(tuple(records), (), (), (), None, None, ())

    premises = [tree for tree in trees[:-1] if tree is not None]
    found = extract(
        [phrase for tree in premises for phrase in phrases_of(tree)],
        phrases_of(trees[-1]),
        tuple((m.a, m.b, m.relation) for m in merges),
    )
    sign = {p.text: ("" if found.polarity_of[p.id] else "~") for p in found.phrase_of.values()}
    symbol = {p.text: found.symbol_of[p.id] for p in found.phrase_of.values()}

    def literal_of(phrase: str) -> str:
        return f"{sign[phrase]}{symbol[phrase]}"

    traced = [
        (clause, record.id)
        for record, tree in zip(records[:-1], trees[:-1], strict=True)
        if tree is not None
        for clause in premise_clauses(tree, literal_of)
    ]
    kb = tuple(clause for clause, _ in traced)
    # Reversed, so the FIRST sentence to produce a clause is the one that wins the key.
    source_of = {clause: sentence for clause, sentence in reversed(traced)}
    goal = tuple(goal_clauses(trees[-1], literal_of))
    entailment = check(kb, goal)
    # Relevance refuses an inconsistent KB itself, so the guard here is the second of two.
    relevant = (
        None
        if entailment.verdict is Verdict.INCONSISTENT_PREMISES
        else filter_clauses(kb, goal, entailment)
    )
    facts = tuple(Fact(f.symbol, tuple((p.id, p.text) for p in f.phrases)) for f in found.facts)
    return Analysis(
        tuple(records),
        facts,
        kb,
        goal,
        entailment,
        relevant,
        found.warnings + entailment.warnings,
        source_of,
    )


def state_of(
    found: Analysis,
    *,
    paragraph: str,
    conclusion: str,
    mode: str = "practice",
    exercise_id: str | None = None,
    mastery: dict[Skill, float] | None = None,
    done_ids: tuple[str, ...] = (),
    merges: tuple[MergeChoice, ...] = (),
) -> State:
    """Build the session a client round-trips, and assign the clause ids.

    **This is the only place clause ids are assigned**, and it has to be: `State` is written by
    this module alone (v2.11), and ids live on `ClauseRec`. An earlier draft had the edge number
    the board as well, which would have meant the CLI and the API each inventing their own `c1`
    -- and a session saved by one client reading differently in the other. `app.view.Board` reads
    these ids back; it never mints one.

    Premises first in paragraph order, then the negated goal, so `c1` is the first premise and the
    last id is always the goal. `origin` distinguishes the three kinds for the Explanation panel.
    """
    clauses, relevant = [], []
    kept = set(found.relevance.kept) if found.relevance else set(found.kb)
    for index, clause in enumerate([*found.kb, *found.goal], start=1):
        goal = clause in set(found.goal)
        record = ClauseRec(
            id=f"c{index}",
            literals=canonical(clause),
            origin="goal" if goal else "given",
            source_sentence_id=found.source_of.get(clause),
        )
        clauses.append(record)
        if goal or clause in kept:
            relevant.append(record.id)
    return State(
        mode=mode,
        exercise_id=exercise_id,
        # "facts", not "prove". The Facts confirmation screen is section 14's explicit safety
        # net for the biggest known limitation -- a connective inside a fact phrase mis-splits
        # silently, and seeing the extracted facts is the only thing that makes it visible. A
        # session that opened straight onto the board would skip it, which is how a student would
        # end up proving something about a fact they never agreed to.
        stage="read" if found.entailment is None else "facts",
        paragraph=paragraph,
        conclusion=conclusion,
        facts=found.facts,
        sentences=found.sentences,
        merges_applied=merges,
        translations=(),
        clauses=tuple(clauses),
        relevant_ids=tuple(relevant),
        mastery=dict(mastery or {}),
        hint_level=0,
        done_ids=done_ids,
        solved=False,
        # The `Entailment` itself, enum and all. Core has ONE spelling of a verdict; translating
        # it to "entails" / "does_not_follow" for a client is presentation, and belongs at the
        # edge (v2.11). An earlier version kept a `_STATUS` table here to do it.
        entailment=found.entailment,
    )


# ------------------------------- hint-level tracking and the A4 reset (v2.7)


def record_hint(state: State) -> State:
    """Charge a hint. The ladder tops out at 3 rather than wrapping."""
    return replace(state, hint_level=min(state.hint_level + 1, 3))


def record_clause(state: State, clause: ClauseRec) -> State:
    """Add a derived clause, resetting the hint level because the board has changed.

    Section 4: the level resets on a clause being added. The old hint was about a position that no
    longer exists, and charging the next step as hinted would punish the student for help they
    did not get. Deriving the empty clause solves the exercise.

    `relevant_ids` gains the new clause too (section 6.5's filter only ever ran over the ORIGINAL
    premises, so a clause the student just derived was never in it). "not needed for this
    conclusion" is a claim about premises, not about something the student derived while working
    toward the goal -- leaving a derived clause out of this set would mislabel it instead.
    """
    solved = not clause.literals
    return replace(
        state,
        clauses=(*state.clauses, clause),
        relevant_ids=(*state.relevant_ids, clause.id),
        hint_level=0,
        solved=solved or state.solved,
        stage="explain" if solved else state.stage,
    )


def record_translation(state: State, sentence_id: str, formula: str, diagnosis_code: str) -> State:
    """Record one Translate-stage attempt (M2, section 9).

    A retry replaces the earlier attempt at the same sentence rather than appending a second one
    -- section 9 scores the attempt the student leaves on screen, not every guess along the way.
    """
    kept = tuple(t for t in state.translations if t.sentence_id != sentence_id)
    return replace(
        state, translations=(*kept, Translation(sentence_id, formula, "done", diagnosis_code))
    )


def enter_stage(state: State, stage: str) -> State:
    """Move to `stage`, resetting the hint level only if the stage actually changed."""
    if stage == state.stage:
        return state
    return replace(state, stage=stage, hint_level=0)


def change_merges(state: State, merges: tuple[MergeChoice, ...], confirmed: bool) -> State:
    """Apply a merge change, discarding the work it invalidates (v2.7 A4).

    Symbols are re-assigned from scratch on every merge (v2.6 A1), so a translation or a proof
    built on the old assignment is no longer ABOUT the same propositions. Keeping it would be
    worse than losing it: the board would silently mean something else. The student therefore
    confirms first, because they cannot see what is at risk.

    Mastery, `done_ids` and the exercise survive -- those are about the student, not this board,
    and losing them would punish a correction.
    """
    if state.stage in ("translate", "prove", "explain") and not confirmed:
        raise ResetRequired("changing a merge discards this proof; confirm before applying")
    return replace(
        state,
        stage="facts",
        merges_applied=merges,
        translations=(),
        clauses=(),
        relevant_ids=(),
        hint_level=0,
        solved=False,
    )
