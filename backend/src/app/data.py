"""The only module that reads a data file (docs/HLD.md section 4).

Core reads no file (v2.4). Every data file is loaded here, validated, and handed to core as plain
data. This module owns no logic -- it validates and stops.

**Validation is in two layers, and the split is deliberate** (S3 refactor).

*Structure* is a Pydantic model: does the file have the right shape, the schema version we
understand, strings where strings belong, and values from the right small set? Pydantic is allowed
HERE because this is the edge; `test_scaffold_imports_and_core_uses_only_stdlib` imports every core
submodule in a clean subprocess and fails if pydantic ever reaches core.

*Semantics* stay explicit code, because every one of them is a cross-check against something else
in the system and that argument has to be readable:

  - evidence TOTALITY, both ways -- every trigger `logic.Code` can produce has a row, and no row
    exists for a trigger nothing produces (a rule the team believes is in force while being dead);
  - the non-evidence rule, both ways -- a scoring row that observes nothing is a dead feedback
    path, and a parse failure that started scoring would punish a student for the grammar's limits;
  - the PLACEHOLDER CONTRACT -- every `{name}` in a template is one `render.py` supplies, and every
    name it supplies is used by some template;
  - the bank's `expected_entailment` cross-check, which lives in `test_bank.py` because it needs
    the whole pipeline to decide.

**Why fail-fast at all.** `tutor.py` indexes the evidence table with no default and no fallback,
because a default would score a skill the student's action never tested. The price is that an
incomplete table is a `KeyError` in front of a student, mid-session, on whichever trigger is
missing. Checking once at startup turns that into a refusal to boot.
"""

import json
from pathlib import Path
from string import Formatter
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.core.english import ErrorCode
from src.core.entail import Verdict
from src.core.logic import Code
from src.core.models import Exercise, Skill

DATA = Path(__file__).resolve().parents[3] / "data"
POLICY_PATH = DATA / "policy.yaml"
BANK_PATH = DATA / "exercises.json"
BANDS_PATH = DATA / "difficulty.json"
MESSAGES_PATH = DATA / "messages.yaml"

Said = Annotated[str, Field(min_length=1)]
Observation = Literal["right", "wrong"] | None

# The three triggers that are legitimately NOT evidence (HLD section 9): a refused sentence was
# not assessed, a merge has no ground truth because the user owns what their words mean, and
# asking for help is not an answer.
_NON_EVIDENCE = frozenset({"parse_failure", "merge", "hint"})
# How `step.VALID` splits on productivity. `unknown` is the work-budget case, where STRATEGY is
# genuinely unobserved and must never be guessed wrong (section 6.6).
_VALID_SPLITS = ("productive", "unproductive", "unknown")
_TRANSLATE_OUTCOMES = ("CORRECT", "CORRECT_CONTRAPOSITIVE", "ERROR")
_CLAIM_OUTCOMES = ("CLAIM_ACCEPTED", "CLAIM_REJECTED")
# Every transport-error code the API can return. Declared HERE rather than imported from
# `api.main`, because `app/` must not depend on an adapter -- and a test asserts the two agree,
# which is a better guarantee than an import: it fails if either side adds a code alone.
API_CODES = frozenset(
    {
        "SCHEMA_INVALID",
        "UNKNOWN_FIELD",
        "STATE_VERSION_MISMATCH",
        "TAMPERED_STATE",
        "UNKNOWN_CLAUSE",
        "WRONG_STAGE",
        "FACTS_NOT_CONFIRMED",
        "ALREADY_FINISHED",
        "RESET_REQUIRED",
        "PAYLOAD_TOO_LARGE",
        "BAD_DATA_FILE",
        "INTERNAL_ERROR",
        "NOT_IMPLEMENTED",
    }
)

# Which `{placeholders}` `render.py` supplies, per message group. The CONTRACT between
# `messages.yaml` and the renderer, checked both ways: a template using an unknown name is a crash
# in front of a student, and a name nobody uses is a dead argument or an unfinished template.
SUPPLIED = {
    "step": {"missing", "extra"},
    "productivity": set(),
    "hint": {"clauses", "resolvent"},
    "claim": set(),
    # Not scored (section 9: a merge confirmation has no ground truth, and leaving the Facts
    # screen is agreement, not an answer), so one trigger with no placeholders.
    "confirm": set(),
    "error": {"sentence"},
    "entailment": {"row"},
    "warning": {"phrase"},
    "cli": {"exercise", "topic", "band", "commands", "sentence"},
    # No placeholders. A transport error returns `{code, message, details?}`: the message is the
    # human sentence and `details` carries the machine specifics as its own field, so there is
    # nothing to interpolate. The startup check caught the first draft, which declared a
    # `{detail}` nobody used.
    "api": set(),
}


class DataError(ValueError):
    """Base for every data-file refusal, so an adapter has one thing to catch at startup."""


class PolicyError(DataError):
    """Raised when `data/policy.yaml` is missing, malformed or incomplete."""


class BankError(DataError):
    """Raised when the bank or the derived bands are missing, malformed or self-contradictory."""


class MessageError(DataError):
    """Raised when `data/messages.yaml` is missing a code, or uses an unsupplied placeholder."""


# ------------------------------------------------------------------ layer 1: structure (Pydantic)


# The one version of each file we understand. Declared on the models rather than in
# `core/config.py`, because core never reads a data file and a file-format version is not one of
# the numeric limits rule 11 is about. `test_every_data_file_declares_the_version_we_accept`
# cross-checks the shipped files against these, so the two cannot drift.
SCHEMA = 1


class _File(BaseModel):
    """Every data file: strict, so a stray key is an error rather than a silent no-op."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyFile(_File):
    schema_version: Literal[SCHEMA]
    # `dict[str, dict[str, Observation]]` and not a model per skill: the skill NAMES come from the
    # `Skill` enum, and duplicating them here would give the enum a second home to drift from. The
    # skill set is checked against the enum in `_check_rows` instead.
    evidence: dict[str, dict[str, Observation]]


class MessagesFile(BaseModel):
    """The groups are open-ended, so the sections arrive as extras and are typed in one go."""

    model_config = ConfigDict(extra="allow")
    schema_version: Literal[SCHEMA]

    def sections(self) -> dict[str, dict[str, str]]:
        from pydantic import TypeAdapter

        return TypeAdapter(dict[str, dict[str, Said]]).validate_python(self.model_extra or {})


class ExerciseRow(_File):
    id: Said
    topic: Said
    paragraph: Said
    conclusion: Said
    expected_entailment: Literal["entails", "does_not_follow"]
    expected_merges: list[tuple[Said, Said]] = []
    covers: list[Said] = []


class BankFile(_File):
    schema_version: Literal[SCHEMA]
    exercises: Annotated[list[ExerciseRow], Field(min_length=1)]
    # The bank's own header, for whoever opens the file. Not data the program uses.
    README: list[str] = Field(default=[], alias="_README")


class BandsFile(_File):
    schema_version: Literal[SCHEMA]
    README: str = Field(default="", alias="_README")
    bands: dict[str, Literal["short", "medium", "long"]]


def _parse(path: Path, model: type[BaseModel], kind: type[DataError], text: bool) -> BaseModel:
    """Read, parse and structurally validate. One preamble for four files.

    Pydantic's message already names the offending field and shows the offending value, so it is
    passed through rather than summarised -- the log has to be enough to fix the file from.
    """
    if not path.is_file():
        raise kind(f"{path}: not found")
    body = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(body) if text else json.loads(body)
    except (yaml.YAMLError, json.JSONDecodeError) as problem:
        raise kind(f"{path}: not valid {'YAML' if text else 'JSON'}: {problem}") from problem
    try:
        return model.model_validate(raw)
    except ValidationError as problem:
        raise kind(f"{path}: {problem}") from problem


# -------------------------------------------------------------- layer 2: semantics (explicit)


def expected_triggers() -> set[str]:
    """Every trigger the system can produce, derived from the enums rather than from the file.

    Deriving it from `policy.yaml` would make the check agree with the file by construction,
    which is the one thing it must not do.
    """
    triggers = {f"step.{code.value}" for code in Code if code is not Code.VALID}
    triggers |= {f"step.VALID.{split}" for split in _VALID_SPLITS}
    triggers |= {f"claim_not_provable.{outcome}" for outcome in _CLAIM_OUTCOMES}
    triggers |= {f"translate.{outcome}" for outcome in _TRANSLATE_OUTCOMES}
    return triggers | set(_NON_EVIDENCE)


def load_policy(path: Path | None = None) -> dict[str, dict[str, str | None]]:
    """The evidence table as plain data, or raise `PolicyError` naming what is wrong."""
    path = POLICY_PATH if path is None else path
    table = _parse(path, PolicyFile, PolicyError, text=True).evidence

    want = expected_triggers()
    _require(not (gap := want - set(table)), path, f"no row for {sorted(gap)}")
    _require(not (dead := set(table) - want), path, f"unreachable rows {sorted(dead)}")
    skills = {skill.value for skill in Skill}
    for trigger, row in table.items():
        # The symmetric difference, not a bare "wrong skills": the realistic edit is a fifth skill
        # added to the enum with one row left behind, and the log has to say which skill.
        _require(
            not (named := set(row) ^ skills),
            path,
            f"row {trigger} must name every skill, not {sorted(named)}",
        )
        # Both directions, and the reason is pedagogical rather than tidy (OQ2).
        observes = set(row.values()) != {None}
        _require(observes == (trigger not in _NON_EVIDENCE), path, f"{trigger}: wrong evidence")

    # Copied row by row so two callers never share a mutable row: the API loads once at startup
    # and passes the table into core on every request.
    return {trigger: dict(row) for trigger, row in table.items()}


def required_messages() -> dict[str, set[str]]:
    """Which templates must exist, derived from the enums rather than from the file."""
    return {
        "step": {code.value for code in Code},
        "productivity": set(_VALID_SPLITS),
        "hint": {f"HINT_{n}" for n in (1, 2, 3)}
        | {f"HINT_NOT_FOLLOW_{n}" for n in (1, 2, 3)}
        | {"HINT_FALLBACK", "HINT_UNAVAILABLE"},
        "claim": set(_CLAIM_OUTCOMES),
        "confirm": {"FACTS_CONFIRMED"},
        "error": {code.value for code in ErrorCode},
        "entailment": {verdict.name for verdict in Verdict} | {"counterexample"},
        # The adapter's own chrome. Listed so `cli.py` cannot acquire a sentence of its own.
        # Transport errors (section 8's HTTP rows). Derived from the API's own status table
        # rather than listed here, so a new status cannot be added without wording -- the same
        # rule the diagnosis codes follow against `logic.Code`.
        "api": API_CODES,
        "cli": {
            "banner",
            "help",
            "commands",
            "prompt",
            "paragraph",
            "conclusion",
            "header",
            "facts",
            "board",
            "mastery",
            "not_needed",
            "unplayable",
            "say_no",
            "solved",
            "finished",
            "bad_step",
            "unknown_clause",
            "own_topic",
            "confirm_prompt",
            "bad_merge",
        },
    }


def _fields(text: str) -> set[str]:
    """A template's `{placeholder}` names, parsed by the formatter that substitutes them."""
    return {name for _, name, _, _ in Formatter().parse(text) if name}


def load_messages(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Every user-facing template, validated against the codes and placeholders in play."""
    path = MESSAGES_PATH if path is None else path
    try:
        sections = _parse(path, MessagesFile, MessageError, text=True).sections()
    except ValidationError as problem:  # raised by sections(), outside _parse's try
        raise MessageError(f"{path}: {problem}") from problem

    for group, wanted in required_messages().items():
        missing = wanted - set(sections.get(group, {}))
        _require(not missing, path, f"{group} has no template for {sorted(missing)}", MessageError)
    for group, table in sections.items():
        for key, text in table.items():
            unknown = _fields(text) - SUPPLIED.get(group, _fields(text))
            _require(
                not unknown,
                path,
                f"{group}.{key} uses {sorted(unknown)}, which the renderer does not supply",
                MessageError,
            )
    for group, supplied in SUPPLIED.items():
        used = {name for text in sections.get(group, {}).values() for name in _fields(text)}
        unused = supplied - used
        _require(not unused, path, f"{group} templates never use {sorted(unused)}", MessageError)
    return sections


def load_bank(path: Path | None = None) -> tuple[tuple[Exercise, ...], dict]:
    """The bank as core dataclasses, plus the authoring metadata the tests check it against.

    Two return values on purpose. `Exercise` carries exactly the four fields the design model
    names, and difficulty is deliberately absent (v2.8 A4a) -- it is computed from the shortest
    proof. `expected_entailment` and `expected_merges` are the AUTHOR'S CLAIMS, checked against the
    pipeline by `test_bank.py`; core must never see them, or a wrong claim would become the answer.
    """
    path = BANK_PATH if path is None else path
    rows = _parse(path, BankFile, BankError, text=False).exercises

    ids = [row.id for row in rows]
    duplicates = {name for name in ids if ids.count(name) > 1}
    _require(not duplicates, path, f"duplicate exercise id {sorted(duplicates)}", BankError)
    exercises = tuple(Exercise(r.id, r.paragraph, r.conclusion, r.topic) for r in rows)
    meta = {
        row.id: {
            "expected_entailment": row.expected_entailment,
            "expected_merges": [tuple(pair) for pair in row.expected_merges],
            "covers": tuple(row.covers),
        }
        for row in rows
    }
    return exercises, meta


def load_bands(path: Path | None = None) -> dict[str, str]:
    """Difficulty bands, DERIVED by scripts/difficulty.py and never hand-written.

    A missing file is a named error rather than an empty mapping: `next_exercise` degrades
    gracefully on an unbanded exercise, so an empty mapping would silently turn band selection off
    for the whole bank instead of saying the derived data had not been generated.
    """
    path = BANDS_PATH if path is None else path
    return dict(_parse(path, BandsFile, BankError, text=False).bands)


def _require(
    condition: object, path: Path, complaint: str, kind: type[DataError] = PolicyError
) -> None:
    """Raise `kind` naming the file and the row, so a bad data file is fixable from the log."""
    if not condition:
        raise kind(f"{path}: {complaint}")
