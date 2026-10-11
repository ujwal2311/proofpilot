"""Request and response envelopes, and the canonical JSON form of a session.

**The `State` field list is declared ONCE**, in `core/models.py`. `TypeAdapter` validates and
serialises the core dataclasses directly, so there is no parallel Pydantic model of a session to
drift from the real one. v2.10 kept `State` in core because the CLI drives core without a server;
the cost of that decision used to be a second declaration of sixteen fields, and this is what
removes it.

Only the ENVELOPES are hand-written, because they are genuinely the API's own: what a client
sends, what it gets back, and the discriminated union of actions.

**`state_version` lives here, not in `State`** (v2.11). The browser keeps a session in
localStorage, so a stale object has to be refused at the boundary — but that is a transport
concern, and a field in the domain model that only one client has any use for was the wrong home
for it. A request carrying the wrong version is refused with `STATE_VERSION_MISMATCH`.

**Canonical output.** `dump_state` sorts every mapping key, so the same session always serialises
to the same bytes. That is what makes the round-trip property test assert something: "lossless"
without "canonical" would pass on output that differed between runs.
"""

from dataclasses import fields
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from src.core.models import MergeChoice, State

# Bumped on ANY change to the `State` field list. The browser sends back what it stored, so a
# version it does not recognise means its copy predates a shape change and must be discarded.
STATE_VERSION = 1

# One adapter per core type, built once at import. `TypeAdapter` on a dataclass gives validation,
# JSON serialisation and a JSON schema (which is what `/docs` renders) from the dataclass itself.
STATE = TypeAdapter(State)
MERGES = TypeAdapter(tuple[MergeChoice, ...])

# The field names a session may carry, taken from the dataclass so the two cannot drift.
STATE_FIELDS = frozenset(f.name for f in fields(State))


class UnknownField(ValueError):
    """A session carrying a field this version does not define (-> 422)."""


def _refuse_unknown_fields(raw: object) -> None:
    """Refuse an invented field rather than ignoring it.

    Pydantic's `extra="forbid"` cannot be used here: it has to be set on the type, and the type is
    a core dataclass that must stay pydantic-free (`test_scaffold_imports_and_core_uses_only_stdlib`
    imports every core submodule in a clean subprocess and fails if pydantic reaches it). Checking
    the keys costs four lines and names the offending field, which pydantic's message does not.

    It matters because ignoring is the dangerous default: a browser posting back a field this
    version does not know about has a stale or tampered copy either way, and accepting the rest
    would mean validating a session while silently discarding part of what arrived.
    """
    if isinstance(raw, dict) and (unknown := sorted(set(raw) - STATE_FIELDS)):
        raise UnknownField(f"{unknown}")


def dump_state(state: State) -> dict:
    """A session as canonical JSON-ready data: enum values named, every mapping key sorted.

    `mode="json"` turns `Skill` keys into their string values and the `Verdict` enum into its
    name, which is where the enum becomes a client-facing string -- at the edge, never in core.
    """
    return _sorted(STATE.dump_python(state, mode="json"))


def load_state(raw: object) -> State:
    """Validate a client's session back into the core dataclass.

    Raises `UnknownField` for a field this version does not define, or `ValidationError` for a
    missing one, a wrong type or a malformed nested record.
    """
    _refuse_unknown_fields(raw)
    return STATE.validate_python(raw)


def _sorted(value: object) -> object:
    """Every mapping key in dictionary order, recursively. Sequence order is left alone.

    Sequences carry meaning here -- `done_ids` is a log and `clauses` is append-only -- so sorting
    them would destroy information. Only mapping key order is arbitrary, and that is the only
    thing normalised.
    """
    if isinstance(value, dict):
        return {key: _sorted(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted(item) for item in value]
    return value


# ----------------------------------------------------------------------------- the actions


class _Body(BaseModel):
    """Every envelope: strict, so a misspelled field is refused rather than silently ignored."""

    model_config = ConfigDict(extra="forbid")


class StepAction(_Body):
    """One proposed resolution step. Literals are validated by core, not by a pattern here."""

    type: Literal["step"]
    clause_a: str
    clause_b: str
    resolvent: list[str]


class HintAction(_Body):
    type: Literal["hint"]
    level: Literal[1, 2, 3]


class ClaimAction(_Body):
    type: Literal["claim_not_provable"]


class TranslateAction(_Body):
    """M2. Valid only in the Translate stage, which `tutor.advance` enforces."""

    type: Literal["translate"]
    sentence_id: str
    formula: str


# Discriminated on `type`, so a bad action names the field that is wrong instead of reporting four
# parallel failures (HLD section 8: one `/act` surface, not one endpoint per action).
Action = Annotated[
    StepAction | HintAction | ClaimAction | TranslateAction,
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- the envelopes


class NextRequest(_Body):
    state_version: int = STATE_VERSION
    state: dict | None = None


class ParseRequest(_Body):
    state_version: int = STATE_VERSION
    paragraph: str
    conclusion: str
    merges: list[MergeChoice] = []


class ActRequest(_Body):
    state_version: int = STATE_VERSION
    state: dict
    action: Action


class NextResponse(_Body):
    state: dict | None
    done: bool


class ParseResponse(_Body):
    """Section 8. `error` is a top-level halt; a per-sentence refusal rides inside `state`."""

    state: dict
    warnings: list[str] = []
    error: str | None = None


class ActResponse(_Body):
    code: str
    message: str
    state: dict
    extras: dict = {}


class Problem(_Body):
    """The body of every 4xx. One shape, so a client has one thing to read."""

    code: str
    message: str
