"""The HTTP adapter: parse a body, call `app`, return JSON. No decisions and no wording.

    python -m uvicorn src.api.main:app --reload    # from backend/

Four endpoints (HLD section 8), stateless: the whole session round-trips in every request body.
No auth, no cookies, no server-side session — a reload of the server loses nothing, because it was
holding nothing.

Every judgment comes from `core` through `app`, and every sentence from `data/messages.yaml`
through `app.render`. `test_adapters_hold_no_user_facing_wording` parses this file and the CLI and
fails on any string that reads like a sentence, which is what stops the browser and the terminal
drifting apart about what the same outcome is called.

**The error model is section 8's rule, implemented as exception handlers rather than as
`try`/`except` at each endpoint.** The rule is: *would this be true regardless of the student's
answer?* → HTTP status. *Is this itself the teaching content?* → 200 with a code. A handler per
exception type keeps that decision in one readable place, and means a new endpoint cannot forget
to map an error it did not know about.
"""

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src import app as edge
from src.api import schemas
from src.api.schemas import ActRequest, NextRequest, ParseRequest
from src.app.audit import Tampered, audit
from src.app.data import DataError
from src.app.render import clause_english_map
from src.core import search, session, tutor
from src.core.bkt import is_done
from src.core.english import ParseError
from src.core.entail import Verdict
from src.core.logic import diagnose, normalize_literal
from src.core.tutor import FactsNotConfirmed, TransitionError

# Both spellings of the dev server: a browser may resolve `localhost` to either, and a CORS list
# naming only one fails for half the team with a message that does not mention CORS.
ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

RUNTIME: dict[str, edge.Runtime] = {}

# Pilot event log (opt-in, HLD section 11's E5). Off by default: a line is written only when
# PROOFPILOT_PILOT_LOG is set AND the request carries an X-Pilot-Id header, so a normal dev or
# CI run never touches disk here. Edge-only by construction -- core.session is never told this
# happened, and the log never carries a paragraph, a conclusion, or anything a student typed.
PILOT_LOG_ENABLED = bool(os.environ.get("PROOFPILOT_PILOT_LOG"))
PILOT_LOG_DIR = Path(__file__).resolve().parents[3] / "docs" / "pilot" / "logs"


class MissingPilotId(ValueError):
    """Pilot logging is on, but this request carries no X-Pilot-Id header.

    The log must never write a line with no participant attached (section 11, E5) -- so a request
    missing the header is refused outright rather than silently logged thin or silently skipped.
    """


def _require_pilot_id(request: Request) -> str | None:
    """The pilot id header, or raise if logging is on and the request did not send one.

    A no-op when PROOFPILOT_PILOT_LOG is off: this must never affect a normal dev or CI request.
    """
    pilot_id = request.headers.get("x-pilot-id")
    if PILOT_LOG_ENABLED and not pilot_id:
        raise MissingPilotId("no X-Pilot-Id header")
    return pilot_id


def _pilot_log(request: Request, action: str, code: str, state: dict | None) -> None:
    """One JSONL line: pilot_id, timestamp, action, result code, hint level, stage. Nothing else.

    `pilot_id` is the participant code from the protocol (P1..P10, typed once per session), never
    a name -- and `docs/pilot/logs/` is gitignored, so even an anonymous line never reaches git.
    """
    if not PILOT_LOG_ENABLED:
        return
    pilot_id = request.headers.get("x-pilot-id")
    if not pilot_id:
        return
    PILOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = {
        "pilot_id": pilot_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "code": code,
        "hint_level": (state or {}).get("hint_level"),
        "stage": (state or {}).get("stage"),
    }
    with (PILOT_LOG_DIR / "pilot.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Validate every data file BEFORE the first request can arrive.

    A malformed policy table or a missing message template must refuse to start the server, not
    surface as a `KeyError` mid-session on whichever path happens to be unlucky (see
    `app/data.py`). Startup is the honest place to fail.
    """
    RUNTIME["edge"] = edge.Runtime.load()
    yield
    RUNTIME.clear()


api = FastAPI(title="ProofPilot", version="1", lifespan=lifespan)
api.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])
app = api  # uvicorn target


@api.middleware("http")
async def limit_body_size(request: Request, call_on):
    """Refuse an oversized body, by BOTH the declared length and the bytes that actually arrive.

    Two checks, because either alone is defeated trivially. `Content-Length` is the cheap one and
    it rejects the honest oversized request before a byte of body is read -- but a client can lie
    about it, or omit it entirely with chunked encoding. So the body is also read and measured.

    `request.body()` is cached by Starlette, so reading it here costs nothing downstream: the
    endpoint gets the same bytes rather than a consumed stream.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > schemas.MAX_BODY_BYTES:
        return _problem(PayloadTooLarge, f"content-length {declared}")
    body = await request.body()
    if len(body) > schemas.MAX_BODY_BYTES:
        return _problem(PayloadTooLarge, f"{len(body)} bytes")
    return await call_on(request)


def runtime() -> edge.Runtime:
    return RUNTIME["edge"]


def _check_version(sent: int) -> None:
    if sent != schemas.STATE_VERSION:
        raise StateVersionMismatch(f"{sent} != {schemas.STATE_VERSION}")


class StateVersionMismatch(ValueError):
    """The client's stored session predates a shape change; it must discard and restart."""


class PayloadTooLarge(ValueError):
    """A request body over the limit (-> 413)."""


# -------------------------------------------------------------------------------- endpoints


@api.get("/api/health")
def health() -> dict:
    return {"ok": True}


@api.post("/api/next")
def next_exercise(body: NextRequest) -> dict:
    """The next exercise to offer, or `done`. Practice mode only (section 8)."""
    _check_version(body.state_version)
    here = runtime()
    previous = schemas.load_state(body.state) if body.state else None
    if previous is not None:
        audit(previous)
    mastery = previous.mastery if previous else here.fresh_mastery()
    seen = previous.done_ids if previous else ()

    if is_done(mastery, here.params):
        return {"state": None, "done": True}
    chosen = tutor.next_exercise(here.bank, here.bands, mastery, seen)
    if chosen is None:
        return {"state": None, "done": True}

    found = edge.prepare(chosen.paragraph, chosen.conclusion)
    fresh = session.state_of(
        found,
        paragraph=chosen.paragraph,
        conclusion=chosen.conclusion,
        exercise_id=chosen.id,
        mastery=mastery,
        done_ids=(*seen, chosen.id),
    )
    return {
        "state": schemas.dump_state(fresh),
        "clause_english": clause_english_map(fresh),
        "done": False,
    }


@api.post("/api/parse")
def parse(body: ParseRequest, request: Request) -> dict:
    """Run the section 7 ordering once and return the session it produces.

    Serves both modes, and is called a second time with `merges` after a manual merge. Merges are
    never inferred (v2.6 A1).
    """
    _check_version(body.state_version)
    _require_pilot_id(request)
    # Strictly validated into core dataclasses here. The envelope carries `list[dict]` because a
    # STRICT envelope would demand actual `MergeChoice` instances and a JSON body only ever has
    # objects -- so the conversion has to happen in the one place that knows how.
    merges = schemas.load_merges(body.merges)
    found = edge.prepare(body.paragraph, body.conclusion, merges)
    fresh = session.state_of(
        found,
        paragraph=body.paragraph,
        conclusion=body.conclusion,
        mode="own_question",
        merges=merges,
    )
    say = runtime().render
    dumped = schemas.dump_state(fresh)
    code = fresh.entailment.verdict.name if fresh.entailment else "UNPLAYABLE"
    _pilot_log(request, "parse", code, dumped)
    return {
        "state": dumped,
        "clause_english": clause_english_map(fresh),
        "warnings": [say.warning(raw) for raw in found.warnings],
        "fol_message": say.fol_outcome(fresh.fol_result) if fresh.fol_result else None,
        "error": None,
    }


@api.post("/api/act")
def act(body: ActRequest, request: Request) -> dict:
    """One student action against a stored session. The discriminated union routes it."""
    _check_version(body.state_version)
    _require_pilot_id(request)
    state = schemas.load_state(body.state)
    audit(state)
    if state.solved:
        raise AlreadyFinished(state.exercise_id or "own")
    kind = body.action.type
    tutor.advance(state.stage, kind)  # raises TransitionError -> 400
    result = _ACTIONS[kind](state, body.action)
    _pilot_log(request, kind, result.get("code", ""), result.get("state"))
    return result


def _verdict_of(state) -> Verdict:
    """The verdict the truth table already reached, read back off the stored session.

    V-2 depends on this (section 6.6): a search must never run when the goal is unreachable, and
    the answer is already in the session rather than something to recompute.
    """
    return state.entailment.verdict if state.entailment else Verdict.ENTAILED


def _step(state, action) -> dict:
    from src.app.view import Board

    board = Board.from_state(state)
    for name in (action.clause_a, action.clause_b):
        if name not in board:
            raise UnknownClause(name)
    claimed = frozenset(normalize_literal(token) for token in action.resolvent)
    before = board.clauses()
    found = diagnose(board[action.clause_a], board[action.clause_b], claimed, before)

    productive = None
    after = state
    if found.code.value == "VALID":
        if _verdict_of(state) is Verdict.ENTAILED:
            productive = search.productive(before, before | {claimed})
        from src.core.logic import canonical
        from src.core.models import ClauseRec

        record = ClauseRec(f"c{len(state.clauses) + 1}", canonical(claimed), "derived", None)
        after = session.record_clause(state, record)
    trigger = tutor.step_trigger(found.code, productive)
    after = _score(after, trigger, state.hint_level > 0)
    return {
        "code": found.code.value,
        "message": runtime().render.step(found, productive),
        "state": schemas.dump_state(after),
        "clause_english": clause_english_map(after),
        "extras": {"valid": found.code.value == "VALID", "productive": productive},
    }


def _hint(state, action) -> dict:
    board = _board(state)
    plan = tutor.plan_hint(board.clauses(), _verdict_of(state), action.level)
    charged = _score(session.record_hint(state), "hint", False)
    return {
        "code": plan.code,
        "message": runtime().render.hint(plan, board.names()),
        "state": schemas.dump_state(charged),
        "clause_english": clause_english_map(charged),
        "extras": {"available": True, "level": plan.level},
    }


def _claim(state, _action) -> dict:
    accepted = _verdict_of(state) is not Verdict.ENTAILED
    code, message = runtime().render.claim(accepted)
    after = _score(state, f"claim_not_provable.{code}", state.hint_level > 0)
    counterexample = state.entailment.counterexample if state.entailment else None
    return {
        "code": code,
        "message": message,
        "state": schemas.dump_state(after),
        "clause_english": clause_english_map(after),
        "extras": {"accepted": accepted, "counterexample": counterexample},
    }


def _translate(state, _action) -> dict:
    """M2. The Translate stage is reachable, but the check itself lands at S6."""
    raise NotImplementedUntilM2("translate")


def _confirm_facts(state, _action) -> dict:
    """Leave the Facts stage. Not scored: agreeing with the extracted facts is not an answer.

    The destination comes from `tutor.advance`, which `act` has already called to check the
    action is legal -- so the stage this moves to is the transition table's, never this file's.
    `act` also means a proving action in "facts" never reaches here: `tutor.advance` raises
    `FactsNotConfirmed` for those before this handler is ever looked up.
    """
    moved = session.enter_stage(state, tutor.advance(state.stage, "confirm_facts"))
    return {
        "code": "FACTS_CONFIRMED",
        "message": runtime().render.text["confirm"]["FACTS_CONFIRMED"],
        "state": schemas.dump_state(moved),
        "clause_english": clause_english_map(moved),
        "extras": {"stage": moved.stage},
    }


def _merge(state, action) -> dict:
    """Change the merge grouping -- the v2.7 A4 reset path, reachable from Prove as well as Facts.

    `tutor.advance` has already checked `("prove"|"facts", "merge")` is legal before this handler
    runs, and the client only sends this action after its OWN "this discards your proof" dialog
    was confirmed -- so `change_merges` always applies here, never raises `ResetRequired`. It is
    still called rather than skipped: it is the one place the v2.7 A4 reset is defined, and
    skipping it would mean this handler re-deriving by hand what fields survive a merge change.
    """
    merges = schemas.load_merges(action.merges)
    reset = session.change_merges(state, merges, confirmed=True)
    found = edge.prepare(reset.paragraph, reset.conclusion, merges)
    fresh = session.state_of(
        found,
        paragraph=reset.paragraph,
        conclusion=reset.conclusion,
        mode=reset.mode,
        exercise_id=reset.exercise_id,
        mastery=reset.mastery,
        done_ids=reset.done_ids,
        merges=merges,
    )
    return {
        "code": "MERGE_RESET",
        "message": runtime().render.text["confirm"]["MERGE_RESET"],
        "state": schemas.dump_state(fresh),
        "clause_english": clause_english_map(fresh),
        "extras": {"stage": fresh.stage},
    }


_ACTIONS = {
    "step": _step,
    "hint": _hint,
    "claim_not_provable": _claim,
    "confirm_facts": _confirm_facts,
    "translate": _translate,
    "merge": _merge,
}


def _board(state):
    from src.app.view import Board

    return Board.from_state(state)


def _score(state, trigger: str, hinted: bool):
    here = runtime()
    moved = tutor.apply_evidence(state.mastery, trigger, hinted, here.policy, here.params)
    from dataclasses import replace

    return replace(state, mastery=moved)


# -------------------------------------------------------- the error model (section 8)
#
# The rule: "would this be true regardless of the student's answer?" -> an HTTP status.
# "Is this itself the teaching content?" -> 200 with a code. Diagnoses, hints, claims and
# entailment verdicts are all teaching content and never appear here.
#
# As handlers rather than per-endpoint try/except, so the mapping is one readable table and a new
# endpoint cannot forget an error it did not know about.


class UnknownClause(ValueError):
    """A clause id that is not on this board -- a tampered or stale request, not a wrong answer."""


class AlreadyFinished(ValueError):
    """An action against a solved session (section 8: 409)."""


class NotImplementedUntilM2(ValueError):
    """A reachable route whose core module lands in a later block."""


# exception type -> (status, code). The code is what a client branches on; the message comes from
# the exception, because every one of these carries the offending value and the client log needs
# it. These are NOT student-facing feedback, so they are not in messages.yaml.
STATUS = {
    ParseError: (422, "SCHEMA_INVALID"),
    ValidationError: (422, "SCHEMA_INVALID"),
    RequestValidationError: (422, "SCHEMA_INVALID"),
    schemas.UnknownField: (422, "UNKNOWN_FIELD"),
    PayloadTooLarge: (413, "PAYLOAD_TOO_LARGE"),
    Exception: (500, "INTERNAL_ERROR"),
    UnknownClause: (400, "UNKNOWN_CLAUSE"),
    Tampered: (400, "TAMPERED_STATE"),
    # FactsNotConfirmed is checked FIRST by Starlette's MRO-based handler lookup because it is a
    # subclass of TransitionError registered under its own exact type -- so this row's position
    # in the dict does not matter, but it is listed right after TransitionError for a reader.
    TransitionError: (400, "WRONG_STAGE"),
    FactsNotConfirmed: (400, "FACTS_NOT_CONFIRMED"),
    session.ResetRequired: (409, "RESET_REQUIRED"),
    AlreadyFinished: (409, "ALREADY_FINISHED"),
    StateVersionMismatch: (409, "STATE_VERSION_MISMATCH"),
    MissingPilotId: (400, "PILOT_ID_REQUIRED"),
    DataError: (500, "BAD_DATA_FILE"),
    NotImplementedUntilM2: (501, "NOT_IMPLEMENTED"),
}


def _problem(kind: type, details: str | None) -> JSONResponse:
    """The one error envelope: `{code, message, details?}`.

    `message` comes from `messages.yaml`, so every sentence a person may read lives in one
    reviewable file. `details` is the machine specifics and is omitted when there are none -- a
    500 carries no details at all, deliberately.

    **The message lookup catches everything.** `runtime()` can itself be the thing that failed --
    a data-file error at startup is reported through this very function -- and a first draft
    caught only `KeyError`/`LookupError`. Injecting a `RuntimeError` into `runtime()` produced a
    500 with an EMPTY BODY: the handler raised while handling, and the client got something it
    could not parse. An error path that can fail is not an error path, so the fallback is total.
    """
    status, code = STATUS[kind]
    try:
        message = runtime().render.text["api"][code]
    except Exception:  # noqa: BLE001 -- deliberate: a bare code beats an unparseable 500
        message = code
    body: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


# The two handled explicitly below are skipped here: FastAPI dispatches `RequestValidationError`
# and `Exception` specially, and registering them twice would make which handler wins depend on
# registration order.
for _kind in (k for k in STATUS if k not in (RequestValidationError, ValidationError, Exception)):

    @api.exception_handler(_kind)
    async def _handle(_request: Request, problem: Exception, kind: type = _kind) -> JSONResponse:
        # `kind` is bound as a default: without it every handler would close over the LAST loop
        # value and report one code for all nine. The classic late-binding bug, and ruff's B023
        # rule is enabled to catch it if this is ever rewritten as a closure.
        return _problem(kind, str(problem))


# ------------------------------------------------- one envelope for EVERY error (S4.1 item 3)
#
# Including the two that are easy to leave out, and which are the ones a client actually trips:
# FastAPI's own `RequestValidationError` (a malformed body, raised before any endpoint runs) and
# an unhandled exception. Without these two, a client would meet three different error shapes and
# have to branch on all three.
#
# The message comes from `messages.yaml` via `app.render`, so there is one reviewable place where
# every sentence a person might read is written -- transport errors included.


def _fields_at_fault(problem: ValidationError | RequestValidationError) -> str:
    """Which field was wrong, as a dotted path. One line, not pydantic's multi-line dump.

    A client needs to know WHERE; it does not need the library's full report, and a details
    string with embedded newlines is awkward to show in a browser. The leading element of `loc`
    is dropped because it is the request part ("body"), which is never news.
    """
    # FastAPI prefixes `loc` with the request part ("body"), which is never news; a
    # `ValidationError` raised inside an endpoint has no such prefix. Dropping the first element
    # unconditionally reported "body" for every bad session field, naming nothing.
    skip = 1 if isinstance(problem, RequestValidationError) else 0
    where = {".".join(str(part) for part in error["loc"][skip:]) for error in problem.errors()}
    return ", ".join(sorted(p for p in where if p)) or "body"


@api.exception_handler(RequestValidationError)
async def _schema_invalid(_request: Request, problem: RequestValidationError) -> JSONResponse:
    """A body FastAPI itself rejected, before any endpoint ran."""
    return _problem(RequestValidationError, _fields_at_fault(problem))


@api.exception_handler(ValidationError)
async def _state_invalid(_request: Request, problem: ValidationError) -> JSONResponse:
    """A session that parsed as JSON but is not a valid one. Same envelope, same shape."""
    return _problem(ValidationError, _fields_at_fault(problem))


@api.exception_handler(Exception)
async def _internal(_request: Request, problem: Exception) -> JSONResponse:
    """The last resort: 500, with NO details.

    A stack trace in a response body is an information leak and tells a student nothing. The
    exception still propagates to the server log, where it belongs -- this only controls what
    crosses the wire.
    """
    return _problem(Exception, None)
