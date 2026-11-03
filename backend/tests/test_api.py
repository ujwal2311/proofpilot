"""The four endpoints, the error model, and the two properties that matter (HLD section 8).

The API is a TRANSPORT. Every judgment it reports came from `core` and every sentence from
`data/messages.yaml`, so these tests do not re-check logic that `test_tutor.py` and
`test_session*.py` already cover. What they check is what only the API can get wrong:

  * the CONTRACT -- four endpoints, the shapes section 8 specifies, `/docs` renders;
  * the ERROR MODEL -- section 8's rule, that "would this be true regardless of the student's
    answer?" is an HTTP status and "is this the teaching content?" is a 200 with a code. Every row
    of `main.STATUS` is reached by a real request, because a mapping nobody exercises is a mapping
    that is wrong;
  * V-2 THROUGH THE WIRE -- the API calls `search.productive` itself, so it has its own chance to
    search a non-entailing board. Asserted by counting calls;
  * STATELESSNESS -- the same request twice gives the same answer, because the server holds
    nothing between them.
"""

import copy

import pytest
from fastapi.testclient import TestClient
from src.api import main, schemas
from src.core.models import Skill

ACT = "/api/act"


@pytest.fixture(scope="module")
def client():
    # `with` runs the lifespan, which is what validates the data files. A bare TestClient would
    # skip it and every test would run against an unloaded runtime.
    with TestClient(main.app) as ready:
        yield ready


@pytest.fixture
def facts(client) -> dict:
    """A fresh practice session, which opens on the FACTS stage."""
    return client.post("/api/next", json={}).json()["state"]


@pytest.fixture
def board(client, facts) -> dict:
    """The same session with the facts confirmed, so it is ready to prove.

    A session now opens on Facts, not Prove (S5): the Facts confirmation screen is section 14's
    safety net for a connective inside a fact phrase, and a session that opened on the board would
    skip it. So the fixture does what a student does -- it confirms first.
    """
    answer = client.post(ACT, json={"state": facts, "action": {"type": "confirm_facts"}})
    assert answer.status_code == 200, answer.json()
    return answer.json()["state"]


def hint(client, state: dict, level: int = 1, accepted: list[str] | None = None):
    action = {"type": "hint", "level": level}
    if accepted is not None:
        action["accepted"] = accepted
    return client.post(ACT, json={"state": state, "action": action})


# ========================================================================= the four endpoints


def test_health_is_ok(client) -> None:
    assert client.get("/api/health").json() == {"ok": True}


def test_next_offers_the_first_unseen_short_exercise(client) -> None:
    body = client.post("/api/next", json={}).json()
    assert body["done"] is False
    assert body["state"]["exercise_id"] == "ex-01"
    assert body["state"]["stage"] == "facts", "a session opens on the facts screen, not the board"
    assert body["state"]["done_ids"] == ["ex-01"], "the offered exercise is recorded as seen"


def test_next_carries_mastery_and_history_forward(client, board) -> None:
    # Statelessness in practice: the client posts the session back, and the server reads the
    # student's progress out of it rather than remembering anything.
    moved = {**board, "mastery": {"CLASH": 0.9, "RESOLVE": 0.9, "STRATEGY": 0.9}}
    body = client.post("/api/next", json={"state": moved}).json()
    assert body["state"]["mastery"] == moved["mastery"]
    assert body["state"]["done_ids"][:1] == ["ex-01"]


def test_next_reports_done_when_every_skill_is_mastered(client, board) -> None:
    mastered = {**board, "mastery": dict.fromkeys(("CLASH", "RESOLVE", "STRATEGY"), 0.99)}
    body = client.post("/api/next", json={"state": mastered}).json()
    assert body == {"state": None, "done": True}


def test_parse_runs_the_whole_pipeline_and_returns_a_session(client) -> None:
    body = client.post(
        "/api/parse",
        json={"paragraph": "If it rains then we get wet. It rains.", "conclusion": "We get wet."},
    ).json()
    state = body["state"]
    assert state["mode"] == "own_question"
    assert [f["symbol"] for f in state["facts"]] == ["A", "B"]
    assert state["entailment"]["verdict"] == "ENTAILED"
    assert [c["id"] for c in state["clauses"]] == ["c1", "c2", "c3"]
    assert body["error"] is None
    assert body["sentence_errors"] == {}


def test_parse_keeps_a_refused_sentence_with_its_code(client) -> None:
    # Per-sentence errors are 200 with a code inside the session, not an HTTP error: a refused
    # sentence is teaching content (section 8, section 3.4). Mixed "and"/"or" with no bracketing
    # word is refused by BOTH grammars -- "Every student passes." would no longer do, since FOL
    # mode now shows that one "ok" (HLD S18.7's Facts-panel fix, test_fol_message... below).
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "It rains. It rains and it is cold or it is windy.",
            "conclusion": "We get wet.",
        },
    )
    assert body.status_code == 200
    statuses = [(s["status"], s["error_code"]) for s in body.json()["state"]["sentences"]]
    assert ("error", "AMBIGUOUS_AND_OR") in statuses


def test_parse_renders_a_refused_sentence_s_error_as_prose(client) -> None:
    # The gap this closes: the web UI showed the bare AMBIGUOUS_AND_OR code with no rephrasing
    # hint, while the CLI already rendered it through Renderer.error(). `sentence_errors` is
    # `Renderer.sentence_errors` keyed by sentence id, reusing error()'s existing wording verbatim.
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "It rains. It rains and it is cold or it is windy.",
            "conclusion": "We get wet.",
        },
    ).json()
    refused = next(s for s in body["state"]["sentences"] if s["error_code"] == "AMBIGUOUS_AND_OR")
    assert body["sentence_errors"] == {
        refused["id"]: (
            'mixing "and" with "or" in one sentence is ambiguous. Split it into two sentences.'
        )
    }


def test_parse_carries_a_fol_result_through_the_wire(client) -> None:
    # HLD S18.7 Phase 8b, through the real API -- not calling fol_prove() or session.analyse()
    # directly. TypeAdapter(State) picks up State.fol_result automatically -- no schema change
    # was needed for THAT to appear in the response, only for the rendered `fol_message` below.
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human.",
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    fol_result = body["state"]["fol_result"]
    assert fol_result is not None
    assert fol_result["outcome"] == "proved"
    assert isinstance(fol_result["step_count"], int)


def test_parse_reaches_facts_stage_when_the_conclusion_itself_is_quantified(client) -> None:
    # Bug found live, 2026-11-03: `state_of`'s stage derivation (session.py) only ever checked
    # the PROPOSITIONAL entailment, which is None whenever the conclusion sentence itself uses a
    # quantifier word -- core.english refuses those unconditionally, regardless of FOL mode. A
    # session stuck on "read" has no ("read", "confirm_facts") transition, so "These facts are
    # right -- start proving" always raised WRONG_STAGE for this entire (ordinary) class of FOL
    # exercise. Every FOL case tested before this had a ground, unquantified conclusion, which is
    # why it went unnoticed. This paragraph exercises all three quantifier constructs the FOL
    # grammar supports (all...who, no, some) and is independently confirmed PROVED in 4 steps.
    body = client.post(
        "/api/parse",
        json={
            "paragraph": (
                "All students who study pass. No teacher is a student. Some student studies."
            ),
            "conclusion": "Some student passes.",
        },
    ).json()
    assert body["state"]["logic_mode"] == "fol"
    assert body["state"]["fol_result"] == {"outcome": "proved", "step_count": 4}
    assert body["state"]["stage"] == "facts"
    confirmed = client.post(ACT, json={"state": body["state"], "action": {"type": "confirm_facts"}})
    assert confirmed.status_code == 200, confirmed.json()


def test_parse_reaches_facts_stage_for_an_ordinary_propositional_session(client) -> None:
    # The regression guard for the fix above: a session with NO fol_result at all must still
    # reach "facts" exactly as before -- the stage check now reads `fol_result` ALONGSIDE
    # `entailment`, not instead of it.
    body = client.post(
        "/api/parse",
        json={"paragraph": "If it rains then we get wet. It rains.", "conclusion": "We get wet."},
    ).json()
    assert body["state"]["fol_result"] is None
    assert body["state"]["stage"] == "facts"


def test_parse_carries_logic_mode_through_the_wire(client) -> None:
    # Regression: logic_mode lived only on Analysis (session.py-local) and never reached State,
    # so state.logic_mode was always undefined on the client -- the ReadFacts.jsx framing note
    # that depends on it could never have shown. Confirmed over the real API, not session.analyse().
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human.",
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    assert body["state"]["logic_mode"] == "fol"


def test_parse_renders_a_refused_sentence_s_error_as_prose_in_fol_mode(client) -> None:
    # `SentenceRec.error_code` is always one of core.english's own codes regardless of
    # `logic_mode` (render.py's own docstring) -- so a sentence that fails BOTH grammars inside
    # an otherwise FOL-mode session must still render through the same `error()` wording.
    body = client.post(
        "/api/parse",
        json={
            "paragraph": (
                "Every human is mortal. Socrates is a human and it is raining or it is snowing."
            ),
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    assert body["state"]["logic_mode"] == "fol"
    refused = next(s for s in body["state"]["sentences"] if s["error_code"] == "AMBIGUOUS_AND_OR")
    assert body["sentence_errors"][refused["id"]] == (
        'mixing "and" with "or" in one sentence is ambiguous. Split it into two sentences.'
    )


def test_parse_fol_message_is_rendered_from_messages_yaml_not_the_raw_code(client) -> None:
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human.",
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    # The rendered sentence, same wording data/messages.yaml's fol.proved template carries --
    # not the raw "proved" code a client would otherwise have to translate itself.
    assert "Valid" in body["fol_message"]
    assert "step" in body["fol_message"]
    assert "proved" not in body["fol_message"]


def test_parse_fol_message_is_null_when_fol_result_is_null(client) -> None:
    body = client.post(
        "/api/parse",
        json={"paragraph": "If it rains then we get wet. It rains.", "conclusion": "We get wet."},
    ).json()
    assert body["fol_message"] is None


def test_parse_fol_result_is_null_for_an_ordinary_session(client) -> None:
    body = client.post(
        "/api/parse",
        json={"paragraph": "If it rains then we get wet. It rains.", "conclusion": "We get wet."},
    ).json()
    assert body["state"]["fol_result"] is None


def _fol_board(client, paragraph: str, conclusion: str) -> dict:
    """A FOL-mode session's state, confirmed to the Prove stage -- the own-question analogue of
    the `board` fixture, which only drives the practice bank."""
    parsed = client.post("/api/parse", json={"paragraph": paragraph, "conclusion": conclusion})
    state = parsed.json()["state"]
    assert state["logic_mode"] == "fol", state
    confirmed = client.post(ACT, json={"state": state, "action": {"type": "confirm_facts"}})
    assert confirmed.status_code == 200, confirmed.json()
    return confirmed.json()["state"]


# ------------------------------------------------------------- FOL-aware hint/claim (follow-up to
# ------------------------------------------------------------- the Facts-panel fix, 2026-11-01):
# `claim_not_provable`/`hint` used to consult ONLY the propositional verdict, so an argument the
# FOL engine proved valid could still have "does not follow" scored as CORRECT. Student-specified
# mapping: PROVED/INCONSISTENT -> the claim is wrong (it follows); BUDGET_EXHAUSTED -> unscored,
# never treated as evidence of non-entailment (HLD S18.11.1, semi-decidability).


def test_claim_not_provable_is_rejected_for_a_proved_fol_argument(client) -> None:
    # The propositional kb here is too sparse to entail the goal at all (the quantified premise
    # contributes no clause), so a propositional-only check would have ACCEPTED "does not follow"
    # -- wrong, since the FOL engine proved the argument valid.
    state = _fol_board(client, "Every human is mortal. Socrates is a human.", "Socrates is mortal.")
    claim = client.post(ACT, json={"state": state, "action": {"type": "claim_not_provable"}}).json()
    assert claim["code"] == "CLAIM_REJECTED"
    assert claim["extras"]["accepted"] is False


def test_claim_not_provable_is_unscored_when_the_fol_budget_is_exhausted(client) -> None:
    state = _fol_board(client, "Every bird flies. Tweety is a bird.", "Tweety is yellow.")
    assert state["fol_result"]["outcome"] == "budget_exhausted"
    claim = client.post(ACT, json={"state": state, "action": {"type": "claim_not_provable"}}).json()
    assert claim["code"] == "CLAIM_UNKNOWN"
    assert claim["extras"]["accepted"] is None
    assert claim["state"]["mastery"] == state["mastery"], (
        "a genuinely unknown outcome must not score"
    )


def test_hint_gives_the_next_step_for_a_proved_fol_argument(client) -> None:
    # Was HINT_FOL_FOLLOWS_1 (outcome-only) before step-level hints existed (HLD S18.16.9) --
    # a real derivation exists here, so the step hint now correctly takes priority over the
    # outcome-level fallback. test_fol_hint_falls_back_to_outcome_level_when_budget_exhausted
    # covers the case where it still doesn't apply.
    state = _fol_board(client, "Every human is mortal. Socrates is a human.", "Socrates is mortal.")
    assert hint(client, state).json()["code"] == "HINT_FOL_STEP_1"


def test_hint_is_honest_when_the_fol_budget_is_exhausted(client) -> None:
    state = _fol_board(client, "Every bird flies. Tweety is a bird.", "Tweety is yellow.")
    assert hint(client, state).json()["code"] == "HINT_FOL_UNKNOWN"


def test_claim_and_hint_are_unaffected_for_an_ordinary_propositional_session(client, board) -> None:
    # Regression: the FOL dispatch must never fire for a prop-mode session (ex-01, from the bank).
    claim = client.post(ACT, json={"state": board, "action": {"type": "claim_not_provable"}}).json()
    assert claim["code"] == "CLAIM_REJECTED"  # matches test_act_routes_each_action_type
    assert hint(client, board).json()["code"] == "HINT_1"


def test_parse_renders_a_warning_through_messages_yaml(client) -> None:
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "If it rains then we get wet. It rains.",
            "conclusion": "The bus is late.",
        },
    ).json()
    assert body["warnings"], "a conclusion naming an unseen fact must warn"
    # Rendered, not raw: the client receives a sentence, never a code with a colon in it.
    assert "CONCLUSION_FACT_UNSEEN" not in body["warnings"][0]
    # Regression: facts.py's warning detail used to carry its own "appears in no premise" suffix,
    # which the {phrase} template slot already says in different words ("which no premise does"),
    # so the rendered sentence read as two concatenated templates -- "the bus is late appears in
    # no premise, which no premise does". One mention only, now.
    assert body["warnings"][0].count("no premise") == 1


def test_parse_applies_merges_and_never_infers_them(client) -> None:
    plain = client.post(
        "/api/parse",
        json={"paragraph": "It is hoping. If it is hopping then we win.", "conclusion": "We win."},
    ).json()["state"]
    split = client.post(
        "/api/parse",
        json={
            "paragraph": "It is hoping. If it is hopping then we win.",
            "conclusion": "We win.",
            "merges": [{"a": "p1", "b": "p2", "relation": "different"}],
        },
    ).json()["state"]
    assert len(split["facts"]) > len(plain["facts"]), "the split was not applied"
    assert split["merges_applied"] == [{"a": "p1", "b": "p2", "relation": "different"}]


def test_act_routes_each_action_type(client, board) -> None:
    step = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": "c1", "clause_b": "c2", "resolvent": ["B"]},
        },
    ).json()
    assert step["code"] == "VALID"
    assert step["extras"] == {"valid": True, "productive": True}
    assert len(step["state"]["clauses"]) == len(board["clauses"]) + 1

    assert hint(client, board).json()["code"] == "HINT_1"
    claim = client.post(ACT, json={"state": board, "action": {"type": "claim_not_provable"}}).json()
    assert claim["code"] == "CLAIM_REJECTED"  # ex-01 does follow


def test_merge_from_prove_resets_to_facts(client, board) -> None:
    # The v2.7 A4 reset, now reachable from the API as well as core: a merge changed mid-proof
    # discards the derived work, because symbols are re-assigned from scratch.
    answer = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "merge", "merges": [{"a": "p1", "b": "p2", "relation": "same"}]},
        },
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["code"] == "MERGE_RESET"
    assert body["state"]["stage"] == "facts"
    assert not any(c["origin"] == "derived" for c in body["state"]["clauses"]), (
        "the proof's derived clauses must not survive a merge change"
    )
    assert body["state"]["merges_applied"] == [{"a": "p1", "b": "p2", "relation": "same"}]


def test_merge_regroups_the_facts(client, board) -> None:
    body = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "merge", "merges": [{"a": "p1", "b": "p2", "relation": "same"}]},
        },
    ).json()
    assert len(body["state"]["facts"]) == 1, (
        "p1 (it rains) and p2 (match cancelled) are now one fact"
    )


def test_merge_is_not_scored(client, board) -> None:
    body = client.post(ACT, json={"state": board, "action": {"type": "merge", "merges": []}}).json()
    assert body["state"]["mastery"] == board["mastery"]


def test_act_names_the_mistake_rather_than_reporting_wrong(client, board) -> None:
    body = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": "c2", "clause_b": "c3", "resolvent": ["A"]},
        },
    ).json()
    assert body["code"] == "NO_CLASH"
    assert body["message"], "a diagnosed step must carry its explanation"
    assert body["extras"]["valid"] is False


def test_act_scores_the_action_and_returns_the_moved_mastery(client, board) -> None:
    before = board["mastery"]["CLASH"]
    body = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": "c2", "clause_b": "c3", "resolvent": ["A"]},
        },
    ).json()
    assert body["state"]["mastery"]["CLASH"] < before, "a NO_CLASH step must cost CLASH"
    assert body["state"]["mastery"]["RESOLVE"] == board["mastery"]["RESOLVE"], "only CLASH observed"


def test_a_hint_is_charged_so_the_next_step_scores_as_hinted(client, board) -> None:
    hinted = hint(client, board).json()["state"]
    assert hinted["hint_level"] == 1
    clean = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": "c1", "clause_b": "c2", "resolvent": ["B"]},
        },
    ).json()["state"]["mastery"]["CLASH"]
    after = client.post(
        ACT,
        json={
            "state": hinted,
            "action": {"type": "step", "clause_a": "c1", "clause_b": "c2", "resolvent": ["B"]},
        },
    ).json()["state"]["mastery"]["CLASH"]
    assert after < clean, "the hint rule did not reach the API"


def test_the_docs_and_schema_render(client) -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {"/api/health", "/api/next", "/api/parse", "/api/act"}


# ============================================================== V-2, through the wire


def test_no_search_runs_for_a_non_entailing_session(client, monkeypatch) -> None:
    """BLOCKER V-2 (section 6.6), asserted at the API rather than only in core.

    `main` calls `search.productive` itself when a step is valid, so the edge has its own chance
    to search a board whose goal is unreachable -- which is the defect the short-circuit exists
    to prevent, and it would show up as seconds of latency rather than as a wrong answer.
    """
    body = client.post(
        "/api/parse",
        json={
            "paragraph": "If the hall is booked then the concert happens. The concert happens.",
            "conclusion": "The hall is booked.",
        },
    ).json()
    state = client.post(
        ACT, json={"state": body["state"], "action": {"type": "confirm_facts"}}
    ).json()["state"]
    assert state["entailment"]["verdict"] == "NOT_ENTAILED"

    calls: list[str] = []
    for name in ("distance", "best_next_step", "productive"):
        original = getattr(main.search, name)
        monkeypatch.setattr(
            main.search,
            name,
            lambda *a, _o=original, _n=name, **k: (calls.append(_n), _o(*a, **k))[1],
        )

    for level in (1, 2, 3):
        assert hint(client, state, level).json()["code"] == f"HINT_NOT_FOLLOW_{level}"
    accepted = client.post(
        ACT, json={"state": state, "action": {"type": "claim_not_provable"}}
    ).json()
    assert accepted["code"] == "CLAIM_ACCEPTED"
    assert accepted["extras"]["counterexample"], "the student must be shown the falsifying row"
    assert calls == [], f"V-2 violated through the API: {calls}"


# ====================================================== the error model (section 8), row by row


def test_the_status_table_is_coherent() -> None:
    """A code may be shared, but only by exceptions that mean the same thing to a client.

    `SCHEMA_INVALID` is shared by three: core's `ParseError`, pydantic's `ValidationError` and
    FastAPI's `RequestValidationError`. All three mean "the body is not something I can work
    with", so a client branching on the code is not misled. Everything else is unique.
    """
    codes = [code for _, code in main.STATUS.values()]
    shared = {code for code in codes if codes.count(code) > 1}
    assert shared == {"SCHEMA_INVALID"}, f"unexpectedly shared codes: {sorted(shared)}"
    assert all(400 <= status < 600 for status, _ in main.STATUS.values())


def test_a_wrong_stage_is_refused(client, board) -> None:
    # `hint` is valid only in `prove` (section 8). This is why TRANSLATE evidence is never
    # hint-affected: there is no hint in the Translate stage, by schema and by table.
    #
    # "explain", not "facts": a proving action attempted in "facts" gets the MORE SPECIFIC
    # FACTS_NOT_CONFIRMED (tested below), because that case has its own wording. "explain" has no
    # such special case, so it is the generic wrong-stage refusal.
    body = hint(client, {**board, "stage": "explain"})
    assert body.status_code == 400
    assert body.json()["code"] == "WRONG_STAGE"


def test_a_proving_action_before_confirming_facts_is_the_specific_error(client, facts) -> None:
    # The gap this fix closes: a session used to open straight onto the board, skipping section
    # 14's explicit safety net for a connective mis-splitting a fact phrase silently.
    body = hint(client, facts)
    assert body.status_code == 400
    assert body.json()["code"] == "FACTS_NOT_CONFIRMED"
    assert body.json()["message"] != ""  # a sentence from messages.yaml, not a bare code


def test_confirming_facts_is_not_scored(client, facts) -> None:
    before = facts["mastery"]
    answer = client.post(
        "/api/act", json={"state": facts, "action": {"type": "confirm_facts"}}
    ).json()
    assert answer["code"] == "FACTS_CONFIRMED"
    assert answer["state"]["stage"] == "prove"
    assert answer["state"]["mastery"] == before, "agreeing with the facts is not an answer"


def test_an_unknown_clause_id_is_refused(client, board) -> None:
    body = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": "c9", "clause_b": "c2", "resolvent": ["B"]},
        },
    )
    assert body.status_code == 400
    # One envelope for every error (S4.1): a sentence from messages.yaml plus the machine detail.
    assert body.json()["code"] == "UNKNOWN_CLAUSE"
    assert body.json()["details"] == "c9"


@pytest.mark.parametrize(
    ("label", "patch"),
    [
        (
            "too many clauses",
            lambda s: {"clauses": [{**s["clauses"][0], "id": f"c{n}"} for n in range(21)]},
        ),
        (
            "too many literals",
            lambda s: {"clauses": [{**s["clauses"][0], "literals": list("ABCDEFG")}]},
        ),
        ("foreign symbol", lambda s: {"clauses": [{**s["clauses"][0], "literals": ["Z"]}]}),
        ("duplicate clause id", lambda s: {"clauses": s["clauses"] + [s["clauses"][0]]}),
        ("mastery above 1", lambda s: {"mastery": {**s["mastery"], "CLASH": 1.5}}),
        ("mastery at 0", lambda s: {"mastery": {**s["mastery"], "CLASH": 0.0}}),
        ("hint level out of range", lambda s: {"hint_level": 9}),
        ("relevant id off the board", lambda s: {"relevant_ids": [*s["relevant_ids"], "c99"]}),
    ],
)
def test_section_eight_tamper_conditions_are_refused(client, board, label, patch) -> None:
    """Section 8's 400 list, one request each.

    None of these is a wrong answer, so none is teaching content -- which is exactly why they are
    statuses rather than codes in a 200 body. Each describes a session that could not have been
    produced by this system, so accepting one would mean scoring a student against a fabrication.
    """
    body = hint(client, {**copy.deepcopy(board), **patch(board)})
    assert body.status_code == 400, f"{label} was accepted"
    assert body.json()["code"] == "TAMPERED_STATE"
    assert body.json()["message"], f"{label} was refused without saying why"


def test_an_action_on_a_solved_session_is_refused(client, board) -> None:
    body = hint(client, {**board, "solved": True})
    assert body.status_code == 409
    assert body.json()["code"] == "ALREADY_FINISHED"


def test_a_stale_state_version_is_refused_and_a_current_one_is_not(client, board) -> None:
    """The localStorage staleness check, which lives in the ENVELOPE rather than in `State`.

    Both directions, because a version check that rejects everything is indistinguishable from
    one that rejects nothing until a client tries the happy path.
    """
    stale = client.post("/api/next", json={"state_version": schemas.STATE_VERSION + 1})
    assert stale.status_code == 409
    assert stale.json()["code"] == "STATE_VERSION_MISMATCH"

    current = client.post("/api/next", json={"state_version": schemas.STATE_VERSION})
    assert current.status_code == 200

    # And it is checked on every endpoint that accepts a session, not just the first one written.
    assert (
        client.post(
            ACT, json={"state_version": 99, "state": board, "action": {"type": "hint", "level": 1}}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/parse",
            json={"state_version": 99, "paragraph": "It rains.", "conclusion": "It rains."},
        ).status_code
        == 409
    )


def test_a_malformed_body_is_a_422(client, board) -> None:
    assert client.post(ACT, json={"state": board}).status_code == 422  # no action
    assert (
        client.post(ACT, json={"state": board, "action": {"type": "nonsense"}}).status_code == 422
    )
    assert client.post("/api/parse", json={"paragraph": "x"}).status_code == 422  # no conclusion


def test_an_unparseable_conclusion_is_a_422_not_a_guess(client) -> None:
    # Two sentences in the conclusion box is a refusal, not a guess about which one is the claim.
    body = client.post(
        "/api/parse", json={"paragraph": "It rains.", "conclusion": "We get wet. We go home."}
    )
    assert body.status_code == 422
    assert body.json()["code"] == "SCHEMA_INVALID"


def test_the_m2_action_is_reachable_and_honest_about_not_being_built(client, board) -> None:
    # Better a 501 naming the gap than a 200 with an invented verdict. S6 replaces it.
    body = client.post(
        ACT,
        json={
            "state": {**board, "stage": "translate"},
            "action": {"type": "translate", "sentence_id": "s1", "formula": "A -> B"},
        },
    )
    assert body.status_code == 501
    assert body.json()["code"] == "NOT_IMPLEMENTED"


# ================================================================= transport properties


def test_cors_allows_both_spellings_of_the_dev_server(client) -> None:
    # A browser may resolve `localhost` to either, and a list naming one fails for half the team
    # with a console message that does not mention CORS.
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        body = client.options(
            ACT,
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        assert body.headers.get("access-control-allow-origin") == origin, origin


def test_an_unknown_origin_is_not_allowed(client) -> None:
    body = client.options(
        ACT, headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"}
    )
    assert body.headers.get("access-control-allow-origin") != "http://evil.example"


def test_the_same_request_twice_gives_the_same_answer(client, board) -> None:
    # Stateless (section 8): the server holds nothing between requests, so a repeat is not a
    # second move. A client that retries after a dropped connection depends on this.
    action = {"type": "step", "clause_a": "c1", "clause_b": "c2", "resolvent": ["B"]}
    first = client.post(ACT, json={"state": board, "action": action}).json()
    again = client.post(ACT, json={"state": board, "action": action}).json()
    assert first == again


def test_the_response_state_is_canonical_so_a_client_can_compare_two(client, board) -> None:
    import json

    once = client.post(ACT, json={"state": board, "action": {"type": "hint", "level": 1}}).text
    twice = client.post(ACT, json={"state": board, "action": {"type": "hint", "level": 1}}).text
    assert once == twice
    assert json.loads(once)["state"]["mastery"], "mastery must survive the hop"


def test_the_api_declares_no_mastery_of_a_skill_the_milestone_does_not_teach(client, board) -> None:
    # M1 tracks three skills. A TRANSLATE entry appearing in a returned session would make
    # `is_done` unreachable for a student who never meets the Translate stage.
    assert set(board["mastery"]) == {s.value for s in Skill} - {"TRANSLATE"}


# ================================================================= clause English (HLD change)


def test_clause_english_is_wired_through_the_real_pipeline(client) -> None:
    # Deliberately fresh content -- a warehouse and a generator, nothing used anywhere else in
    # this file -- to prove the rendering generalizes rather than matching a known fixture.
    parsed = client.post(
        "/api/parse",
        json={
            "paragraph": (
                "If the warehouse loses power, the backup generator starts. "
                "The warehouse loses power."
            ),
            "conclusion": "The backup generator starts.",
        },
    ).json()
    # Clauses are already on the board right after parsing, before the student confirms facts --
    # so clause_english must be populated from the very first response, not only after Prove.
    english = parsed["clause_english"]
    by_literals = {tuple(c["literals"]): english[c["id"]] for c in parsed["state"]["clauses"]}
    assert by_literals[("B", "~A")] == (
        "the backup generator starts or not the warehouse loses power"
    )
    assert by_literals[("A",)] == "the warehouse loses power"
    assert by_literals[("~B",)] == "not the backup generator starts"

    # Confirm facts to reach the Prove stage, where "step" is a legal action.
    board = client.post(
        ACT, json={"state": parsed["state"], "action": {"type": "confirm_facts"}}
    ).json()["state"]

    # Step 1: A + (~A or B) -> B. The DERIVED clause must render too, not just the given ones --
    # this is what "updates live after the student's own step" actually means.
    c_a = next(c["id"] for c in board["clauses"] if tuple(c["literals"]) == ("A",))
    c_b = next(c["id"] for c in board["clauses"] if tuple(c["literals"]) == ("B", "~A"))
    stepped = client.post(
        ACT,
        json={
            "state": board,
            "action": {"type": "step", "clause_a": c_a, "clause_b": c_b, "resolvent": ["B"]},
        },
    ).json()
    new_b = next(
        c for c in stepped["state"]["clauses"] if tuple(c["literals"]) == ("B",) and c["id"] != c_b
    )
    assert stepped["clause_english"][new_b["id"]] == "the backup generator starts"

    # Step 2: the derived B + (~B) -> the empty clause, the goal of a refutation.
    c_not_b = next(c["id"] for c in stepped["state"]["clauses"] if tuple(c["literals"]) == ("~B",))
    finished = client.post(
        ACT,
        json={
            "state": stepped["state"],
            "action": {
                "type": "step",
                "clause_a": new_b["id"],
                "clause_b": c_not_b,
                "resolvent": [],
            },
        },
    ).json()
    empty = next(c for c in finished["state"]["clauses"] if c["literals"] == [])
    assert finished["clause_english"][empty["id"]] == "a contradiction"


# ============================================================ FOL step action (HLD S18.16) ===
#
# Six outcomes, none of which may ever reach the generic 500 handler: a malformed answer and
# each of the five FolStepError codes are teaching content (the file's own section-8 rule), so
# every one of them is a 200 with a named code -- proven here the same way V-2 and statelessness
# above are proven, by a real request, not by reading the handler.


def _label_containing(trace, *substrings) -> str:
    """The legend label whose rendered text contains every one of `substrings` -- used instead
    of a hardcoded "F3" so these tests do not depend on exact label numbering, only on the real
    clauses a real paragraph produces."""
    for entry in trace["legend"]:
        if all(s in entry["text"] for s in substrings):
            return entry["label"]
    raise AssertionError(f"no legend entry contains {substrings}: {trace['legend']}")


def _fol_act(
    client,
    state: dict,
    clause_a: str,
    clause_b: str,
    resolvent: str,
    accepted: list[str] | None = None,
):
    return client.post(
        ACT,
        json={
            "state": state,
            "action": {
                "type": "fol_step",
                "clause_a": clause_a,
                "clause_b": clause_b,
                "resolvent": resolvent,
                "accepted": accepted or [],
            },
        },
    )


@pytest.fixture
def socrates_fol_board(client) -> dict:
    """F1: rule, F2: Human(socrates), F3 (negated goal): ¬Mortal(socrates) -- confirmed to the
    Prove stage, the one place `fol_step` is a legal action (tutor.TRANSITIONS, HLD S18.16)."""
    parsed = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human.",
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    confirmed = client.post(
        ACT, json={"state": parsed["state"], "action": {"type": "confirm_facts"}}
    )
    assert confirmed.status_code == 200, confirmed.json()
    return confirmed.json()["state"], parsed["fol_trace"]


def test_fol_step_with_a_malformed_answer_is_a_clean_200_not_a_500(
    client, socrates_fol_board
) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Mortal(1socrates")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "FOL_ANSWER_MALFORMED"
    assert "Mortal(1socrates" in body["message"]


def test_fol_step_not_complementary_is_a_clean_200(client, socrates_fol_board) -> None:
    state, trace = socrates_fol_board
    f2 = _label_containing(trace, "Human(socrates)")
    f3 = _label_containing(trace, "¬Mortal(socrates)")
    response = _fol_act(client, state, f2, f3, "")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "FOL_STEP_NOT_COMPLEMENTARY"
    assert "Human(socrates)" in body["message"] and "¬Mortal(socrates)" in body["message"]


def test_fol_step_no_unifier_is_a_clean_200(client) -> None:
    # "Every human is mortal" is filler, present only so detect_mode() sees a quantifier and
    # reads this paragraph as FOL at all (S18.7: an all-ground paragraph is read as propositional,
    # which is correct behaviour, just not what this test needs) -- the pair under test is
    # Human(socrates) against ¬Human(plato).
    parsed = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human. Plato is not a human.",
            "conclusion": "Socrates is mortal.",
        },
    ).json()
    confirmed = client.post(
        ACT, json={"state": parsed["state"], "action": {"type": "confirm_facts"}}
    ).json()
    trace = parsed["fol_trace"]
    socrates_human = _label_containing(trace, "Human(socrates)")
    not_plato_human = _label_containing(trace, "¬Human(plato)")
    response = _fol_act(client, confirmed["state"], socrates_human, not_plato_human, "")
    assert response.status_code == 200
    assert response.json()["code"] == "FOL_STEP_NO_UNIFIER"


def test_fol_step_double_resolve_is_a_clean_200(client) -> None:
    # Student(ravi) v Lucky(ravi), and its exact double negation -- resolving on EITHER single
    # pivot alone is a tautology (filtered), so the ONLY way to reach the empty clause here is
    # the unsound double-cancel, which is exactly the trap a student claiming victory falls into.
    # Same filler reason as the NO_UNIFIER test above.
    parsed = client.post(
        "/api/parse",
        json={
            "paragraph": (
                "Every human is mortal. Ravi is a student or Ravi is lucky. "
                "Ravi is not a student or Ravi is not lucky."
            ),
            "conclusion": "Ravi passes the exam.",
        },
    ).json()
    confirmed = client.post(
        ACT, json={"state": parsed["state"], "action": {"type": "confirm_facts"}}
    ).json()
    trace = parsed["fol_trace"]
    positive = _label_containing(trace, "Student(ravi)", "Lucky(ravi)")
    negative = _label_containing(trace, "¬Student(ravi)", "¬Lucky(ravi)")
    response = _fol_act(client, confirmed["state"], positive, negative, "")
    assert response.status_code == 200
    assert response.json()["code"] == "FOL_STEP_DOUBLE_RESOLVE"


def test_fol_step_subst_incomplete_is_a_clean_200(client, socrates_fol_board) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Mortal(x)")  # forgot x -> socrates
    assert response.status_code == 200
    assert response.json()["code"] == "FOL_STEP_SUBST_INCOMPLETE"


def test_fol_step_wrong_resolvent_is_a_clean_200(client, socrates_fol_board) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Mortal(plato)")
    assert response.status_code == 200
    assert response.json()["code"] == "FOL_STEP_WRONG_RESOLVENT"


def test_fol_step_valid_is_a_clean_200(client, socrates_fol_board) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Mortal(socrates)")
    assert response.status_code == 200
    assert response.json()["code"] == "VALID"


def test_fol_step_with_an_unknown_clause_label_is_the_existing_unknown_clause_error(
    client, socrates_fol_board
) -> None:
    """Reuses `UnknownClause`, same as propositional -- a stale/tampered label is structural,
    not an answer-dependent outcome, so it is the one case this action DOES raise through."""
    state, _trace = socrates_fol_board
    response = _fol_act(client, state, "F99", "F2", "Mortal(socrates)")
    assert response.status_code == 400
    assert response.json()["code"] == "UNKNOWN_CLAUSE"


# =========================================================== FOL board state (HLD S18.16.8) ===
#
# Stateless by design, same as the rest of this API: the client echoes back its own accumulated
# `accepted` clause texts, never stored server-side. These tests prove a real multi-step proof
# chains to completion, that solved ties into the EXISTING state.solved/AlreadyFinished lock
# (not a new flag), and that a tampered `accepted` entry is refused rather than trusted.


def test_fol_step_accepts_a_prior_derived_clause_and_chains_to_the_empty_clause(
    client, socrates_fol_board
) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    f3 = _label_containing(trace, "¬Mortal(socrates)")

    # Step 1: derive Mortal(socrates) -- NOT the engine's own minimal-derivation path (which
    # resolves F1+F3 first), proving the board does not silently depend on matching it.
    step1 = _fol_act(client, state, f1, f2, "Mortal(socrates)")
    assert step1.status_code == 200
    body1 = step1.json()
    assert body1["code"] == "VALID"
    assert body1["state"]["solved"] is False

    # Step 2: resolve the newly-accepted clause against the negated goal -> the empty clause.
    # Its label must be new (not one of the original legend's), continuing that numbering.
    new_label = f"F{len(trace['legend']) + 1}"
    step2 = _fol_act(client, body1["state"], new_label, f3, "", accepted=["Mortal(socrates)"])
    assert step2.status_code == 200
    body2 = step2.json()
    assert body2["code"] == "VALID"


def test_reaching_the_empty_clause_sets_the_existing_solved_field(
    client, socrates_fol_board
) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    f3 = _label_containing(trace, "¬Mortal(socrates)")
    new_label = f"F{len(trace['legend']) + 1}"

    step1 = _fol_act(client, state, f1, f2, "Mortal(socrates)").json()
    step2 = _fol_act(
        client, step1["state"], new_label, f3, "", accepted=["Mortal(socrates)"]
    ).json()

    assert step2["state"]["solved"] is True
    assert step2["state"]["stage"] == "explain"


def test_once_solved_the_existing_already_finished_lock_applies(client, socrates_fol_board) -> None:
    """No new enforcement was written for this -- `act()`'s pre-existing `if state.solved: raise
    AlreadyFinished` check runs before any action handler, FOL included."""
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    f3 = _label_containing(trace, "¬Mortal(socrates)")
    new_label = f"F{len(trace['legend']) + 1}"

    step1 = _fol_act(client, state, f1, f2, "Mortal(socrates)").json()
    step2 = _fol_act(
        client, step1["state"], new_label, f3, "", accepted=["Mortal(socrates)"]
    ).json()
    assert step2["state"]["solved"] is True

    locked = _fol_act(client, step2["state"], f1, f2, "Mortal(socrates)")
    assert locked.status_code == 409
    assert locked.json()["code"] == "ALREADY_FINISHED"


def test_a_tampered_accepted_entry_is_refused_not_trusted(client, socrates_fol_board) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Mortal(socrates)", accepted=["not valid notation("])
    assert response.status_code == 400
    assert response.json()["code"] == "TAMPERED_STATE"


def test_an_invalid_step_never_mutates_state_so_retry_costs_nothing(
    client, socrates_fol_board
) -> None:
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    response = _fol_act(client, state, f1, f2, "Zebra(socrates)")
    assert response.status_code == 200
    assert response.json()["code"] == "FOL_STEP_WRONG_RESOLVENT"
    assert response.json()["state"] == state  # unchanged, exactly as propositional's own board


# ============================================================ FOL step-level hints (S18.16.9) ==


def test_fol_hint_level_1_names_the_next_canonical_step(client, socrates_fol_board) -> None:
    state, _trace = socrates_fol_board
    response = hint(client, state, level=1, accepted=[])
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "HINT_FOL_STEP_1"
    assert "resolve F" in body["message"]


def test_fol_hint_level_2_adds_the_unifier(client, socrates_fol_board) -> None:
    state, _trace = socrates_fol_board
    response = hint(client, state, level=2, accepted=[])
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "HINT_FOL_STEP_2"
    assert "where x =" in body["message"] or "no substitution needed" in body["message"]


def test_fol_hint_level_3_caps_at_level_2_content(client, socrates_fol_board) -> None:
    state, _trace = socrates_fol_board
    at_2 = hint(client, state, level=2, accepted=[]).json()
    at_3 = hint(client, state, level=3, accepted=[]).json()
    assert at_2["message"] == at_3["message"]


def test_fol_hint_advances_once_a_step_is_derived(client, socrates_fol_board) -> None:
    """Deriving a step -- not asking for a hint -- is what advances which step is hinted."""
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    step1 = _fol_act(client, state, f1, f2, "Mortal(socrates)").json()

    before = hint(client, state, level=1, accepted=[]).json()
    after = hint(client, step1["state"], level=1, accepted=["Mortal(socrates)"]).json()
    assert before["message"] != after["message"]


def test_fol_hint_is_honest_when_the_students_path_has_diverged(client, socrates_fol_board) -> None:
    """The student's own valid first step (F1+F2) is NOT the engine's own canonical first step
    (F1+F3) -- the next canonical step therefore needs a clause the student's board does not
    have. The hint must say so, not point at a clause they cannot see."""
    state, trace = socrates_fol_board
    f1 = _label_containing(trace, "Human(x)", "Mortal(x)")
    f2 = _label_containing(trace, "Human(socrates)")
    step1 = _fol_act(client, state, f1, f2, "Mortal(socrates)").json()

    response = hint(client, step1["state"], level=1, accepted=["Mortal(socrates)"])
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "HINT_FOL_STEP_UNAVAILABLE"


def test_fol_hint_falls_back_to_outcome_level_when_budget_exhausted(client) -> None:
    parsed = client.post(
        "/api/parse",
        json={
            "paragraph": "Every human is mortal. Socrates is a human.",
            "conclusion": "Socrates is a zebra.",
        },
    ).json()
    confirmed = client.post(
        ACT, json={"state": parsed["state"], "action": {"type": "confirm_facts"}}
    ).json()
    response = hint(client, confirmed["state"], level=1, accepted=[])
    assert response.status_code == 200
    assert response.json()["code"] == "HINT_FOL_UNKNOWN"


def test_propositional_hints_are_unaffected_by_the_new_accepted_field(client, board) -> None:
    """The schema addition is optional and FOL-only in effect -- confirm it changes nothing for
    an ordinary propositional session, which never sends `accepted` at all."""
    response = hint(client, board, level=1)
    assert response.status_code == 200
    assert response.json()["code"] in {"HINT_1", "HINT_2", "HINT_3", "HINT_UNAVAILABLE"}
