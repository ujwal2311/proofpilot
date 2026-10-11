"""Tests for core.models -- the dataclasses crossing the edge<->core boundary (HLD section 4.1).

Written before the implementation.

CONTRACT. These types carry data and own no logic. Two properties are worth asserting because
both have bitten this project already:

  1. They are FROZEN and hold tuples, not lists. Purity is then structural rather than promised:
     the API replays a student's merges over a stored state, so a core function that mutated its
     argument would silently corrupt the caller's copy. A frozen dataclass makes that a crash.
  2. `State` matches the HLD section 4 data model exactly -- including that `mastery_history` is
     ABSENT, cut from M1 in v2.10 item 3. A field list is the one thing that drifts invisibly.

`models.py` must read no file; `test_core_layout` already forbids web imports, and the check here
is the narrower one that nothing in core opens anything.
"""

import copy
import dataclasses
import json
import types
import typing
from dataclasses import FrozenInstanceError
from enum import Enum

import pytest
from src.core import models
from src.core.models import ClauseRec, Exercise, Fact, MergeChoice, SentenceRec, Skill, State

DATACLASSES = (Exercise, Fact, MergeChoice, ClauseRec, SentenceRec, State)


def _state() -> State:
    return State(
        schema_version=1,
        mode="practice",
        exercise_id="ex-01",
        stage="prove",
        paragraph="If it rains then we get wet. It rains.",
        conclusion="We get wet.",
        facts=(Fact(symbol="P", phrases=(("p1", "it rains"),)),),
        sentences=(SentenceRec(id="s1", text="It rains.", status="ok"),),
        merges_applied=(),
        translations=(),
        clauses=(ClauseRec(id="c1", literals=("P",), origin="given", source_sentence_id="s1"),),
        relevant_ids=("c1",),
        mastery={Skill.CLASH: 0.3, Skill.RESOLVE: 0.3, Skill.STRATEGY: 0.3},
        hint_level=0,
        done_ids=(),
        solved=False,
        entailment=None,
    )


# ----------------------------------------------------------------------------------------- shape


def test_skill_names_the_four_skills_in_order() -> None:
    # Three active in M1, four in M2. The order is load-bearing: the mastery display and the
    # simulation both iterate it, and a reordering would silently relabel a chart.
    assert [skill.name for skill in Skill] == ["CLASH", "RESOLVE", "STRATEGY", "TRANSLATE"]
    assert [skill.value for skill in Skill] == ["CLASH", "RESOLVE", "STRATEGY", "TRANSLATE"]


def test_every_model_is_a_frozen_dataclass() -> None:
    for kind in DATACLASSES:
        assert dataclasses.is_dataclass(kind), kind
        assert kind.__dataclass_params__.frozen, f"{kind.__name__} must be frozen"


def test_exercise_carries_exactly_the_four_fields_in_the_bank_file() -> None:
    # HLD section 4: difficulty is COMPUTED by scripts/difficulty.py, never stored and never
    # hand-labelled. A fifth field here is how a hand-labelled difficulty would sneak in.
    assert {f.name for f in dataclasses.fields(Exercise)} == {
        "id",
        "paragraph",
        "conclusion",
        "topic",
    }


def test_state_matches_the_hld_data_model() -> None:
    assert {f.name for f in dataclasses.fields(State)} == {
        "schema_version",
        "mode",
        "exercise_id",
        "stage",
        "paragraph",
        "conclusion",
        "facts",
        "sentences",
        "merges_applied",
        "translations",
        "clauses",
        "relevant_ids",
        "mastery",
        "hint_level",
        "done_ids",
        "solved",
        "entailment",
    }


def test_mastery_history_is_absent_from_m1() -> None:
    # Cut in v2.10 item 3: it only ever fed the stretch feature "Why this score?", and BKT needs
    # the posterior, not the sequence that produced it. Asserted rather than assumed, because a
    # field is exactly the kind of thing that gets re-added by habit.
    names = {f.name for f in dataclasses.fields(State)}
    assert "mastery_history" not in names
    assert not hasattr(models, "HistoryItem")


# ---------------------------------------------------------------------------------------- purity


def test_a_model_cannot_be_mutated_in_place() -> None:
    state = _state()
    with pytest.raises(FrozenInstanceError):
        state.stage = "explain"  # type: ignore[misc]


def test_sequence_fields_are_tuples_not_lists() -> None:
    # A frozen dataclass holding a list is only shallowly immutable: `state.facts.append(...)`
    # would still work and would still corrupt the caller. Tuples close that.
    state = _state()
    for name in (
        "facts",
        "sentences",
        "merges_applied",
        "translations",
        "clauses",
        "relevant_ids",
        "done_ids",
    ):
        assert isinstance(getattr(state, name), tuple), f"{name} must be a tuple"


def test_replace_produces_a_new_state_and_leaves_the_original_alone() -> None:
    # The intended way to advance a stage: `dataclasses.replace`, which is why frozen is right
    # rather than merely strict.
    state = _state()
    before = copy.deepcopy(state)
    advanced = dataclasses.replace(state, stage="explain", solved=True)
    assert advanced.stage == "explain" and advanced.solved is True
    assert state == before


def test_models_are_comparable_by_value() -> None:
    # Equality by value is what lets a test assert "the state did not change" at all.
    assert _state() == _state()
    assert Fact(symbol="P", phrases=(("p1", "it rains"),)) == Fact(
        symbol="P", phrases=(("p1", "it rains"),)
    )


# --------------------------------------------------------------- JSON representability (F2)
#
# The BLOCKING round-trip property test -- 200 random States, lossless and canonical across both
# hash seeds -- belongs to S4, where `api/schemas.py` owns the conversion. What belongs HERE is
# the structural precondition that makes such a round-trip possible at all, because that is a
# property of the data model and it can be broken by adding one field.
#
# The failure this guards against is concrete: a `set` or `frozenset` field is not JSON-
# representable, and a `dict` keyed by anything but a string is not either. Both are natural
# things to reach for in a clause-set codebase where `Clause = frozenset[str]`, and neither would
# fail any test above.

JSON_SCALARS = (int, float, str, bool, type(None))


def _is_representable(annotation: object) -> bool:
    """Can this annotation be encoded as JSON without inventing an encoding for it?"""
    if annotation in JSON_SCALARS or annotation is dict:
        return True
    if dataclasses.is_dataclass(annotation):
        # Resolved with get_type_hints rather than reading `field.type`, which is a STRING
        # whenever the module uses postponed annotations -- a string would fall through to the
        # final `return False` and report a perfectly good model as unencodable.
        hints = typing.get_type_hints(annotation)
        return all(_is_representable(hints[f.name]) for f in dataclasses.fields(annotation))
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        # Only if every member's VALUE is a JSON scalar -- that is what gets written out.
        return all(type(m.value) in JSON_SCALARS for m in annotation)

    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin in (tuple, list):
        return all(a is Ellipsis or _is_representable(a) for a in args)
    if origin is dict:
        # A JSON object's keys are STRINGS, so the key rule is stricter than the value rule: an
        # Enum key is fine because its value is a string, but a tuple key is not, even though a
        # tuple is a perfectly good JSON *value*. Collapsing the two rules into one recursive
        # call was the first draft, and it accepted `dict[tuple[str, str], float]`.
        key, value = args
        key_ok = key is str or (
            isinstance(key, type)
            and issubclass(key, Enum)
            and all(type(m.value) is str for m in key)
        )
        return key_ok and _is_representable(value)
    if origin in (types.UnionType, typing.Union):
        return all(_is_representable(a) for a in args)
    return False


def test_every_state_field_is_json_representable() -> None:
    hints = typing.get_type_hints(State)
    for name, annotation in hints.items():
        assert _is_representable(annotation), f"State.{name}: {annotation} cannot be JSON"


def test_the_representability_check_would_actually_reject_a_set_or_a_bad_key() -> None:
    # A guard nobody has seen fail is a guard nobody should trust. `frozenset[str]` is exactly
    # what a clause looks like in this codebase, so it is the realistic mistake.
    assert not _is_representable(frozenset[str])
    assert not _is_representable(set[str])
    assert not _is_representable(dict[tuple[str, str], float])
    assert not _is_representable(tuple[frozenset[str], ...])
    assert _is_representable(dict[Skill, float])
    assert _is_representable(tuple[Fact, ...])


def test_asdict_on_a_state_is_already_json_encodable_once_enum_keys_are_named() -> None:
    # The structural claim, exercised rather than only type-checked: `dataclasses.asdict` plus
    # naming the Skill keys is enough. If it were not, S4's conversion would need an encoding
    # decision, which is the thing this test exists to discover early.
    raw = dataclasses.asdict(_state())
    raw["mastery"] = {skill.value: value for skill, value in raw["mastery"].items()}
    text = json.dumps(raw, sort_keys=True)

    back = json.loads(text)
    assert back["facts"][0]["phrases"] == [["p1", "it rains"]]  # tuples land as lists
    assert back["mastery"]["CLASH"] == 0.3
    # Canonical: the same State always produces the same bytes, which is what makes the S4
    # round-trip assertion meaningful rather than merely usually true.
    assert text == json.dumps(raw, sort_keys=True)


def test_models_reads_no_file() -> None:
    # Core never touches the filesystem (HLD v2.4): data crosses the boundary as these objects,
    # loaded by the edge. A core module that read a file would make core untestable without one.
    #
    # Parsed with `ast`, not grepped. The first version of this test searched the raw source for
    # "json" and failed on the DOCSTRING, which names `exercises.json` to explain who loads it --
    # a check that cannot tell code from prose reports the explanation as the violation.
    import ast

    tree = ast.parse(open(models.__file__, encoding="utf-8").read())
    imported = {
        node.module.split(".")[0] if isinstance(node, ast.ImportFrom) and node.module else None
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"json", "yaml", "pathlib", "io", "os"}, f"models.py imports {imported}"

    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in called, "models.py must not open a file"
