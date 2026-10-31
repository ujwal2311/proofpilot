"""BLOCKING: a session survives the API boundary unchanged, and serialises canonically.

The browser stores a session in localStorage and posts it back on every action. If the round trip
lost a field, or reordered one, the student's work would degrade silently across a reload -- not
crash, degrade: a dropped `done_ids` entry re-offers a finished exercise, a dropped `hint_level`
makes the next step score as unhinted, a reordered `clauses` renames the board under a hint that
has already been given. None of those raise.

So this is a PROPERTY test over randomly built sessions rather than a few examples:

  LOSSLESS   `load_state(dump_state(s)) == s`, for every shape the model allows.
  CANONICAL  `dump_state` produces the same bytes for the same session, every time and in every
             process. Lossless without canonical would pass on output that varied between runs,
             and a client diffing two responses would see phantom changes.

Both are asserted over >= 200 cases, and the whole file is run under both hash seeds by the
determinism CI job -- which is the point of the canonical half, since dict ordering is where a
hash seed would show up.
"""

import json
import random

import pytest
from src.api.schemas import STATE, dump_state, load_state
from src.core import config
from src.core.entail import Entailment, Verdict
from src.core.fol_search import FolProofOutcome, FolSessionResult
from src.core.models import ClauseRec, Fact, MergeChoice, SentenceRec, Skill, State, Translation

CASES = 200
SYMBOLS = "ABCDEFGHIJ"


def _clause(rng: random.Random, index: int) -> ClauseRec:
    size = rng.randint(0, 3)  # 0 is the EMPTY clause, which a solved session contains
    literals = tuple(
        sorted({f"{'~' if rng.random() < 0.5 else ''}{rng.choice(SYMBOLS)}" for _ in range(size)})
    )
    return ClauseRec(
        id=f"c{index}",
        literals=literals,
        origin=rng.choice(("given", "goal", "derived")),
        source_sentence_id=rng.choice((None, f"s{rng.randint(1, 9)}")),
    )


def _sentence(rng: random.Random, index: int) -> SentenceRec:
    ok = rng.random() < 0.8
    return SentenceRec(
        id=f"s{index}",
        text=rng.choice(("It rains.", "If A then B", "We play unless it snows", "")),
        status="ok" if ok else "error",
        error_code=None if ok else rng.choice(("UNPARSEABLE", "AMBIGUOUS_AND_OR", "TOO_LONG")),
        formula=rng.choice((None, "A -> B")),
        symbols=tuple(rng.sample(SYMBOLS, rng.randint(0, 3))),
    )


def _entailment(rng: random.Random) -> Entailment | None:
    """Every verdict, including the two that carry extra payload."""
    if rng.random() < 0.15:
        return None
    verdict = rng.choice(list(Verdict))
    row = None
    if verdict is Verdict.NOT_ENTAILED:
        row = {s: rng.random() < 0.5 for s in rng.sample(SYMBOLS, rng.randint(1, 4))}
    warnings = tuple(
        rng.sample(("CONCLUSION_FACT_UNSEEN: x", "TAUTOLOGICAL_CONCLUSION: y"), rng.randint(0, 2))
    )
    return Entailment(verdict, row, warnings)


def _fol_result(rng: random.Random) -> FolSessionResult | None:
    """None most of the time (propositional sessions), every FolProofOutcome the rest."""
    if rng.random() < 0.7:
        return None
    return FolSessionResult(rng.choice(list(FolProofOutcome)), rng.randint(0, 20))


def random_state(rng: random.Random) -> State:
    """A session of a randomly chosen SHAPE -- not a realistic one, a structurally varied one.

    Deliberately not built by running the pipeline: that would only ever produce the shapes the
    pipeline happens to produce today, and the round trip has to hold for every shape the model
    permits -- including the empty clause, an error sentence, four skills, and a `None` verdict.
    """
    clauses = tuple(_clause(rng, n) for n in range(1, rng.randint(1, 8)))
    skills = rng.sample(list(Skill), rng.randint(0, len(Skill)))
    return State(
        mode=rng.choice(("practice", "own_question")),
        exercise_id=rng.choice((None, f"ex-{rng.randint(1, 12):02d}")),
        stage=rng.choice(("read", "facts", "translate", "prove", "explain")),
        paragraph=rng.choice(("If it rains then we get wet. It rains.", "", "A. B. C.")),
        conclusion=rng.choice(("We get wet.", "", "The bus is late!")),
        facts=tuple(
            Fact(
                symbol=SYMBOLS[n],
                phrases=tuple((f"p{m}", f"phrase {m}") for m in range(rng.randint(1, 3))),
            )
            for n in range(rng.randint(0, 5))
        ),
        sentences=tuple(_sentence(rng, n) for n in range(1, rng.randint(1, 6))),
        merges_applied=tuple(
            MergeChoice(f"p{rng.randint(1, 5)}", f"p{rng.randint(1, 5)}", rel)
            for rel in rng.sample(("same", "opposite", "different"), rng.randint(0, 3))
        ),
        translations=tuple(
            Translation(f"s{n}", rng.choice((None, "R -> C")), rng.choice(("pending", "correct")))
            for n in range(rng.randint(0, 3))
        ),
        clauses=clauses,
        relevant_ids=tuple(c.id for c in clauses if rng.random() < 0.7),
        mastery={skill: round(rng.random(), 6) for skill in skills},
        hint_level=rng.randint(0, 3),
        done_ids=tuple(f"ex-{rng.randint(1, 12):02d}" for _ in range(rng.randint(0, 4))),
        solved=rng.random() < 0.3,
        entailment=_entailment(rng),
        fol_result=_fol_result(rng),
    )


@pytest.fixture(scope="module")
def sessions() -> list[State]:
    rng = random.Random(config.RANDOM_SEED)
    return [random_state(rng) for _ in range(CASES)]


def test_the_round_trip_is_lossless(sessions: list[State]) -> None:
    for state in sessions:
        assert load_state(dump_state(state)) == state


def test_the_round_trip_is_canonical(sessions: list[State]) -> None:
    """The same session serialises to the same BYTES, every time.

    `json.dumps` without `sort_keys`, on purpose: the point is that `dump_state` already ordered
    the keys, not that `json` can order them for us. A client caching on the response body, or
    diffing two of them, depends on this.
    """
    for state in sessions:
        once = json.dumps(dump_state(state))
        assert once == json.dumps(dump_state(state))
        assert once == json.dumps(dump_state(load_state(dump_state(state))))


def test_the_round_trip_survives_a_json_text_hop(sessions: list[State]) -> None:
    # The real path is not dict -> dict: it is dict -> text -> HTTP -> text -> dict. A tuple that
    # arrives back as a list, or a float that loses precision, shows up only here.
    for state in sessions:
        assert load_state(json.loads(json.dumps(dump_state(state)))) == state


def test_every_mapping_key_comes_out_sorted(sessions: list[State]) -> None:
    def check(value: object, where: str) -> None:
        if isinstance(value, dict):
            keys = list(value)
            assert keys == sorted(keys), f"unsorted keys at {where}: {keys}"
            for key, item in value.items():
                check(item, f"{where}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                check(item, f"{where}[{index}]")

    for state in sessions:
        check(dump_state(state), "state")


def test_sequence_order_is_preserved_because_it_carries_meaning(sessions: list[State]) -> None:
    # `done_ids` is a log and `clauses` is append-only with ids attached, so sorting them would
    # destroy information. Only MAPPING key order is arbitrary, and only that is normalised.
    for state in sessions:
        raw = dump_state(state)
        assert tuple(raw["done_ids"]) == state.done_ids
        assert [c["id"] for c in raw["clauses"]] == [c.id for c in state.clauses]


# --------------------------------------------------------------- the generator has to be real


def test_the_generator_actually_varies_the_shape(sessions: list[State]) -> None:
    """A property test over 200 near-identical cases is one case run 200 times.

    Each of these is a shape that broke something, or could: the empty clause only appears in a
    solved session, an error sentence carries a code the happy path never sets, a `None` verdict
    is the unparseable-conclusion case, and a four-skill mastery map is M2.
    """
    assert any(not c.literals for s in sessions for c in s.clauses), "no empty clause generated"
    assert any(r.status == "error" for s in sessions for r in s.sentences), "no error sentence"
    assert any(s.entailment is None for s in sessions), "no undecided entailment"
    assert any(s.entailment and s.entailment.counterexample for s in sessions), "no counterexample"
    assert any(len(s.mastery) == len(Skill) for s in sessions), "never all four skills"
    assert any(not s.mastery for s in sessions), "never an empty mastery map"
    assert any(s.solved for s in sessions) and any(not s.solved for s in sessions)
    assert len({s.stage for s in sessions}) == 5, "not every stage appeared"
    assert any(s.translations for s in sessions), "no translations generated"
    assert any(s.merges_applied for s in sessions), "no merges generated"
    assert len({s.hint_level for s in sessions}) == 4, "not every hint level appeared"


def test_the_case_count_is_what_the_brief_requires(sessions: list[State]) -> None:
    assert len(sessions) >= 200


def test_the_generator_is_seeded_so_a_failure_is_reproducible() -> None:
    # Rule 4. An unseeded generator can expose a bug but cannot reproduce it, which makes a
    # property failure a story rather than a bug report.
    first = [dump_state(random_state(random.Random(config.RANDOM_SEED))) for _ in range(3)]
    again = [dump_state(random_state(random.Random(config.RANDOM_SEED))) for _ in range(3)]
    assert first == again


def test_a_structurally_broken_session_is_refused() -> None:
    """Structure is refused here. SEMANTICS are refused by `api.main.audit` (section 8).

    What this layer catches is a missing field, a wrong type, or a malformed nested record.

    What it does NOT catch, measured rather than assumed: pydantic's default lax mode coerces
    `"3"` to `3`, `"yes"` to `True` and `True` to `1`. That is acceptable at this layer -- the
    browser posts back what it stored, so a scalar arriving as the wrong spelling of the right
    value is harmless -- and it is NOT the tamper check section 8 asks for. Section 8 names
    semantic conditions: an unknown clause id, a foreign symbol, too many clauses, too many
    literals, a wrong stage, mastery outside (0,1). Those are in `test_api.py`.
    """
    from pydantic import ValidationError

    raw = dump_state(random_state(random.Random(config.RANDOM_SEED)))

    with pytest.raises(ValidationError, match="stage"):
        load_state({k: v for k, v in raw.items() if k != "stage"})

    with pytest.raises(ValidationError, match="hint_level"):
        load_state({**raw, "hint_level": "not a number"})

    with pytest.raises(ValidationError):
        load_state({**raw, "clauses": [{"id": "c1"}]})  # a clause with no literals

    # An invented field is refused by NAME. Pydantic's `extra="forbid"` cannot be used -- it has
    # to be set on the type, and the type is a core dataclass that must stay pydantic-free -- so
    # `schemas._refuse_unknown_fields` checks the keys and says which one is wrong.
    from src.api.schemas import UnknownField

    with pytest.raises(UnknownField, match="invented_field"):
        load_state({**raw, "invented_field": 1})


def test_the_adapter_publishes_a_schema_so_docs_can_render_it() -> None:
    # `/docs` is part of the S4 brief. It renders from the JSON schema the adapter derives from
    # the core dataclass, which is the whole reason there is no parallel Pydantic model.
    schema = STATE.json_schema()
    assert "properties" in schema or "$ref" in schema
