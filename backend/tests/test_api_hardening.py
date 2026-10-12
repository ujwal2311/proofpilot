"""S4.1: strict validation, body-size limits, and ONE error envelope for everything.

Three properties the API has to hold that are not about tutoring at all, and each one was added
because the measured behaviour differed from what a docstring claimed:

  STRICT      pydantic's default lax mode turns `"3"` into `3`, `"yes"` into `True` and `3.0` into
              `3`. On a session that arrives from a browser that means a corrupt or tampered field
              becomes a plausible value and the student is scored against it.
  BOUNDED     a request has a maximum size, checked BOTH by the declared length and by the bytes
              that actually arrive -- a client can understate `Content-Length` or omit it.
  ONE SHAPE   every error returns `{code, message, details?}`, including FastAPI's own body
              validation and an unhandled exception. Three shapes would mean a client branching
              on all three, and the two easiest to forget are the two it actually trips.
"""

import pytest
from fastapi.testclient import TestClient
from src.api import main
from src.api.schemas import MAX_CONCLUSION, MAX_PARAGRAPH

ACT = "/api/act"


@pytest.fixture(scope="module")
def client():
    # `raise_server_exceptions=False` so a 500 comes back as a RESPONSE rather than propagating
    # into the test. The point of these tests is what crosses the wire.
    with TestClient(main.app, raise_server_exceptions=False) as ready:
        yield ready


@pytest.fixture
def board(client) -> dict:
    """A session with the facts confirmed, so `hint` is legal in its stage."""
    opened = client.post("/api/next", json={}).json()["state"]
    return client.post(ACT, json={"state": opened, "action": {"type": "confirm_facts"}}).json()[
        "state"
    ]


def hint(client, state: dict, level: int = 1):
    return client.post(ACT, json={"state": state, "action": {"type": "hint", "level": level}})


# ================================================================== 1. strict validation


@pytest.mark.parametrize(
    ("label", "patch"),
    [
        ("string where an int belongs", {"action": {"type": "hint", "level": "1"}}),
        ("string where a version belongs", {"state_version": "1"}),
        ("extra envelope field", {"bogus": 1}),
    ],
)
def test_the_envelope_refuses_a_coerced_value(client, board, label, patch) -> None:
    request = {"state": board, "action": {"type": "hint", "level": 1}, **patch}
    answer = client.post(ACT, json=request)
    assert answer.status_code == 422, f"{label} was accepted"
    assert answer.json()["code"] == "SCHEMA_INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    [("solved", "no"), ("hint_level", "2"), ("hint_level", 2.0), ("mode", 1)],
)
def test_the_session_refuses_a_coerced_value(client, board, field, value) -> None:
    # The session goes through `load_state` rather than an envelope model, and strict mode there
    # had to use `validate_json`: `validate_python(strict=True)` refuses a mapping for a dataclass
    # outright, demanding an actual instance.
    answer = hint(client, {**board, field: value})
    assert answer.status_code == 422, f"{field}={value!r} was accepted"
    assert answer.json()["code"] == "SCHEMA_INVALID"
    assert field in answer.json()["details"], "the refusal must name the field"


def test_a_valid_body_still_passes_in_strict_mode(client, board) -> None:
    # Strictness is only worth having if the honest path still works. A guard that rejects
    # everything is indistinguishable from one that rejects nothing until someone tries.
    assert hint(client, board).status_code == 200
    assert (
        client.post(
            "/api/parse", json={"paragraph": "It rains.", "conclusion": "It rains."}
        ).status_code
        == 200
    )


def test_the_round_trip_still_holds_under_strict_validation(client, board) -> None:
    # The whole reason `validate_json` was needed: strict mode must not reject the server's own
    # output. A session that comes out and goes back in has to be accepted.
    assert hint(client, hint(client, board).json()["state"]).status_code == 200


# ========================================================================= 2. size limits


def test_an_oversized_body_is_refused_by_its_declared_length(client) -> None:
    answer = client.post("/api/parse", json={"paragraph": "A" * 70_000, "conclusion": "x"})
    assert answer.status_code == 413
    assert answer.json()["code"] == "PAYLOAD_TOO_LARGE"
    assert "content-length" in answer.json()["details"]


def test_an_oversized_body_is_refused_even_without_a_length_header(client) -> None:
    """The half that matters: `Content-Length` can be understated or omitted entirely.

    Sent as a generator, which makes httpx use chunked encoding and send no length header at all
    -- so this request can only be caught by measuring the bytes that arrive.
    """

    def chunks():
        yield b'{"paragraph": "' + b"A" * 70_000 + b'", "conclusion": "x"}'

    answer = client.post(
        "/api/parse", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert answer.status_code == 413
    assert answer.json()["code"] == "PAYLOAD_TOO_LARGE"
    assert "bytes" in answer.json()["details"], "caught by the header, not by the stream"


def test_the_largest_legal_paragraph_is_nowhere_near_the_size_limit(client) -> None:
    """The boundary from the other side, so the limit is a limit rather than a wall.

    The first version of this test used `"It rains. " * 100` and got a 422 -- correctly, because
    100 sentences breaks section 3.4's 12-sentence cap. That is the point worth recording: the
    SIZE limits can never be what refuses an honest paragraph. Twelve sentences of thirty words
    is about two kilobytes, so the 64 KB ceiling only ever sees a body nobody typed.
    """
    # A CHAIN, so nine sentences introduce ten facts rather than twenty: section 3.4 also caps
    # distinct facts at ten, and the first draft of this fixture tripped that instead.
    steps = [f"If the step {n} is done then the step {n + 1} is done." for n in range(9)]
    paragraph = " ".join(steps)
    assert len(paragraph) < MAX_PARAGRAPH
    answer = client.post(
        "/api/parse", json={"paragraph": paragraph, "conclusion": "The step 9 is done."}
    )
    assert answer.status_code == 200, answer.json()


def test_a_paragraph_over_its_limit_is_refused(client) -> None:
    answer = client.post(
        "/api/parse", json={"paragraph": "x" * (MAX_PARAGRAPH + 1), "conclusion": "It rains."}
    )
    assert answer.status_code == 422
    assert answer.json()["details"] == "paragraph"


def test_a_conclusion_over_its_limit_is_refused(client) -> None:
    answer = client.post(
        "/api/parse", json={"paragraph": "It rains.", "conclusion": "x" * (MAX_CONCLUSION + 1)}
    )
    assert answer.status_code == 422
    assert answer.json()["details"] == "conclusion"


# ==================================================================== 3. one error envelope


def test_every_error_uses_the_same_envelope(client, board) -> None:
    answers = {
        "RequestValidationError": client.post(ACT, json={"state": board}),
        "Tampered": hint(client, {**board, "hint_level": 9}),
        "AlreadyFinished": hint(client, {**board, "solved": True}),
        "WrongStage": hint(client, {**board, "stage": "facts"}),
        "StateVersionMismatch": client.post("/api/next", json={"state_version": 99}),
        "PayloadTooLarge": client.post(
            "/api/parse", json={"paragraph": "A" * 70_000, "conclusion": "x"}
        ),
    }
    for label, answer in answers.items():
        body = answer.json()
        assert answer.status_code >= 400, label
        assert set(body) <= {"code", "message", "details"}, f"{label}: {sorted(body)}"
        assert body["code"] and body["message"], label
        # A SENTENCE from messages.yaml, not the code repeated back at the client.
        assert body["message"] != body["code"], f"{label} has no wording"
        assert " " in body["message"], label


def test_an_unhandled_exception_is_a_500_with_no_stack_trace(client, monkeypatch) -> None:
    """A stack trace in a response body is an information leak and tells a student nothing."""

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom at /home/secret/path.py line 42")

    monkeypatch.setattr(main.tutor, "next_exercise", explode)
    answer = client.post("/api/next", json={})
    assert answer.status_code == 500
    body = answer.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert "details" not in body, "a 500 must carry no details at all"
    assert "secret" not in answer.text and "Traceback" not in answer.text
    assert " " in body["message"], "it still reads as a sentence, from messages.yaml"


def test_the_error_envelope_survives_the_runtime_itself_being_broken(client, monkeypatch) -> None:
    """An error path that can fail is not an error path.

    `_problem` looks its message up through `runtime()`, and `runtime()` can be the very thing
    that failed -- a data-file error at startup is reported through this function. A first draft
    caught only `KeyError`/`LookupError`, and injecting a `RuntimeError` produced a 500 with an
    EMPTY BODY: the handler raised while handling, and the client got something unparseable.
    """
    monkeypatch.setattr(
        main, "runtime", lambda: (_ for _ in ()).throw(RuntimeError("runtime is gone"))
    )
    answer = client.post("/api/next", json={})
    assert answer.status_code == 500
    assert answer.json() == {"code": "INTERNAL_ERROR", "message": "INTERNAL_ERROR"}
    assert "runtime is gone" not in answer.text


def test_a_422_names_the_field_at_fault(client, board) -> None:
    # `details` exists so a client developer can fix the request. "body" names nothing, and an
    # earlier version returned exactly that for every bad session field, because it dropped the
    # first element of the error location unconditionally.
    assert client.post(ACT, json={"state": board}).json()["details"] == "action"
    assert "solved" in hint(client, {**board, "solved": "no"}).json()["details"]


def test_every_status_code_has_wording_in_messages_yaml() -> None:
    from src.app.data import API_CODES, load_messages

    codes = {code for _, code in main.STATUS.values()}
    assert codes <= API_CODES, f"{sorted(codes - API_CODES)} is not declared in API_CODES"
    said = load_messages()["api"]
    for code in codes:
        assert said[code].strip(), f"{code} has no wording"


def test_the_api_codes_list_matches_the_status_table() -> None:
    # `app/` must not import an adapter, so `API_CODES` is declared there and the two are checked
    # to agree. That is a better guarantee than an import: it fails if EITHER side adds a code.
    from src.app.data import API_CODES

    assert {code for _, code in main.STATUS.values()} == set(API_CODES)
