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

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src import app as edge
from src.api import schemas
from src.api.schemas import ActRequest, NextRequest, ParseRequest
from src.app.audit import Tampered, audit
from src.app.data import DataError
from src.core import search, session, tutor
from src.core.bkt import is_done
from src.core.english import ParseError
from src.core.entail import Verdict
from src.core.logic import diagnose, normalize_literal
from src.core.tutor import TransitionError

# Both spellings of the dev server: a browser may resolve `localhost` to either, and a CORS list
# naming only one fails for half the team with a message that does not mention CORS.
ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

RUNTIME: dict[str, edge.Runtime] = {}


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


def runtime() -> edge.Runtime:
    return RUNTIME["edge"]


def _check_version(sent: int) -> None:
    if sent != schemas.STATE_VERSION:
        raise StateVersionMismatch(f"{sent} != {schemas.STATE_VERSION}")


class StateVersionMismatch(ValueError):
    """The client's stored session predates a shape change; it must discard and restart."""


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
    return {"state": schemas.dump_state(fresh), "done": False}


@api.post("/api/parse")
def parse(body: ParseRequest) -> dict:
    """Run the section 7 ordering once and return the session it produces.

    Serves both modes, and is called a second time with `merges` after a manual merge. Merges are
    never inferred (v2.6 A1).
    """
    _check_version(body.state_version)
    found = edge.prepare(body.paragraph, body.conclusion, tuple(body.merges))
    fresh = session.state_of(
        found,
        paragraph=body.paragraph,
        conclusion=body.conclusion,
        mode="own_question",
        merges=tuple(body.merges),
    )
    say = runtime().render
    return {
        "state": schemas.dump_state(fresh),
        "warnings": [say.warning(raw) for raw in found.warnings],
        "error": None,
    }


@api.post("/api/act")
def act(body: ActRequest) -> dict:
    """One student action against a stored session. The discriminated union routes it."""
    _check_version(body.state_version)
    state = schemas.load_state(body.state)
    audit(state)
    if state.solved:
        raise AlreadyFinished(state.exercise_id or "own")
    kind = body.action.type
    tutor.advance(state.stage, kind)  # raises TransitionError -> 400
    return _ACTIONS[kind](state, body.action)


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
        "extras": {"accepted": accepted, "counterexample": counterexample},
    }


def _translate(state, _action) -> dict:
    """M2. The Translate stage is reachable, but the check itself lands at S6."""
    raise NotImplementedUntilM2("translate")


_ACTIONS = {"step": _step, "hint": _hint, "claim_not_provable": _claim, "translate": _translate}


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
    ParseError: (422, "UNPROCESSABLE"),
    ValidationError: (422, "UNPROCESSABLE"),
    schemas.UnknownField: (422, "UNKNOWN_FIELD"),
    UnknownClause: (400, "UNKNOWN_CLAUSE"),
    Tampered: (400, "TAMPERED_STATE"),
    TransitionError: (400, "WRONG_STAGE"),
    session.ResetRequired: (409, "RESET_REQUIRED"),
    AlreadyFinished: (409, "ALREADY_FINISHED"),
    StateVersionMismatch: (409, "STATE_VERSION_MISMATCH"),
    DataError: (500, "BAD_DATA_FILE"),
    NotImplementedUntilM2: (501, "NOT_IMPLEMENTED"),
}


def _problem(kind: type, detail: str) -> JSONResponse:
    status, code = STATUS[kind]
    return JSONResponse(status_code=status, content={"code": code, "message": detail})


for _kind in STATUS:

    @api.exception_handler(_kind)
    async def _handle(_request: Request, problem: Exception, kind: type = _kind) -> JSONResponse:
        # `kind` is bound as a default: without it every handler would close over the LAST loop
        # value and report one code for all nine. The classic late-binding bug, and ruff's B023
        # rule is enabled to catch it if this is ever rewritten as a closure.
        return _problem(kind, str(problem))
