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


def hint(client, state: dict, level: int = 1):
    return client.post(ACT, json={"state": state, "action": {"type": "hint", "level": level}})


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


def test_parse_keeps_a_refused_sentence_with_its_code(client) -> None:
    # Per-sentence errors are 200 with a code inside the session, not an HTTP error: a refused
    # sentence is teaching content (section 8, section 3.4).
    body = client.post(
        "/api/parse",
        json={"paragraph": "It rains. Every student passes.", "conclusion": "We get wet."},
    )
    assert body.status_code == 200
    statuses = [(s["status"], s["error_code"]) for s in body.json()["state"]["sentences"]]
    assert ("error", "QUANTIFIER_UNSUPPORTED") in statuses


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
