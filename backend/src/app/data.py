"""The edge's data loader: reads the files core is not allowed to touch (docs/HLD.md section 4).

Core reads no file (v2.4). Every data file is loaded here, validated for SHAPE, and handed to
core as plain data. This module owns no logic -- it validates and stops.

**Validation is fail-fast on purpose.** `tutor.py` indexes the evidence table by trigger with no
default and no fallback, because a default would score a skill the student's action never tested.
The price of that choice is that an incomplete table is a `KeyError` in front of a student,
mid-session, on whichever trigger happens to be missing. So the table is checked once, at
startup, against `logic.Code` -- the authority on what a step can actually produce -- and a bad
file refuses to start the server instead of failing later.
"""

import json
from pathlib import Path

import yaml

from src.core import config
from src.core.english import ErrorCode
from src.core.entail import Verdict
from src.core.logic import Code
from src.core.models import Exercise, Skill

DATA = Path(__file__).resolve().parents[3] / "data"
POLICY_PATH = DATA / "policy.yaml"
BANK_PATH = DATA / "exercises.json"
BANDS_PATH = DATA / "difficulty.json"
MESSAGES_PATH = DATA / "messages.yaml"

_LEGAL = {"right", "wrong", None}
# The three triggers that are legitimately NOT evidence (HLD section 9): a refused sentence was
# not assessed, a merge has no ground truth because the user owns what their words mean, and
# asking for help is not an answer. Listed here so the check runs in both directions -- a scoring
# row that observes nothing is a dead feedback path, and one of these three that starts scoring
# would punish a student for the parser's limits.
_NON_EVIDENCE = frozenset({"parse_failure", "merge", "hint"})
# How `step.VALID` splits on productivity. `unknown` is the work-budget case, where STRATEGY is
# genuinely unobserved and must never be guessed wrong (section 6.6).
_VALID_SPLITS = ("productive", "unproductive", "unknown")
_TRANSLATE_OUTCOMES = ("CORRECT", "CORRECT_CONTRAPOSITIVE", "ERROR")
_CLAIM_OUTCOMES = ("CLAIM_ACCEPTED", "CLAIM_REJECTED")


class DataError(ValueError):
    """Base for every data-file refusal, so an adapter has one thing to catch at startup."""


def _read(path: Path, version: int, kind: type[Exception], text: bool = False) -> dict:
    """Exists, parses, and declares the schema version we understand. Four loaders, one preamble.

    `kind` is the caller's named error type: the message has to say which FILE is wrong, and a
    single generic exception would make a bad bank and a bad policy look the same in a log.
    """
    if not path.is_file():
        raise kind(f"{path}: not found")
    body = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(body) if text else json.loads(body)
    except (yaml.YAMLError, json.JSONDecodeError) as problem:
        raise kind(f"{path}: not valid {'YAML' if text else 'JSON'}: {problem}") from problem
    # rule 11: the expected version comes from config.py, never retyped into a message.
    found = raw.get("schema_version") if isinstance(raw, dict) else type(raw).__name__
    if found != version:
        raise kind(f"{path}: schema_version must be {version}, got {found}")
    return raw


class PolicyError(DataError):
    """Raised when `data/policy.yaml` is missing, malformed or incomplete.

    A named error, not an assert: the file is an input from outside the program, so this is
    boundary validation (CLAUDE.md rule 5) and the message has to say which row is wrong.
    """


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
    raw = _read(path, config.POLICY_SCHEMA_VERSION, PolicyError, text=True)
    table = raw.get("evidence")
    _require(isinstance(table, dict), path, "`evidence` must be a mapping of trigger to row")
    _require(not (gap := expected_triggers() - set(table)), path, f"no row for {sorted(gap)}")
    _require(not (dead := set(table) - expected_triggers()), path, f"unreachable rows {dead}")

    skills = {skill.value for skill in Skill}
    for trigger, row in table.items():
        # The symmetric difference, not a bare "wrong skills": the realistic edit is a fifth skill
        # added to the enum with one row left behind, and the log has to say which skill.
        named = set(row) ^ skills if isinstance(row, dict) else {type(row).__name__}
        _require(not named, path, f"{trigger}: rows must name every skill, not {sorted(named)}")
        for skill, value in row.items():
            # Type-checked before the membership test: a nested mapping -- how a mode split would
            # have to be written -- is unhashable and would raise TypeError from `in`.
            legal = isinstance(value, str | None) and value in _LEGAL
            _require(legal, path, f"{trigger}.{skill} is {value!r}, not right/wrong/null")
        # Both directions. A scoring row that observes nothing is a dead feedback path; one of the
        # three non-evidence triggers that starts scoring would punish a student for being
        # refused by the grammar rather than for being wrong (OQ2).
        observes = set(row.values()) != {None}
        _require(observes == (trigger not in _NON_EVIDENCE), path, f"{trigger}: wrong evidence")

    # Copied row by row so two callers never share a mutable row: the API loads once at startup
    # and passes the table into core on every request.
    return {trigger: dict(row) for trigger, row in table.items()}


def _require(condition: object, path: Path, complaint: str) -> None:
    """Raise `PolicyError` naming the file and the row, so a bad policy is fixable from the log."""
    if not condition:
        raise PolicyError(f"{path}: {complaint}")


class BankError(DataError):
    """Raised when `data/exercises.json` is missing, malformed or self-contradictory."""


def load_bank(path: Path | None = None) -> tuple[tuple[Exercise, ...], dict]:
    """The bank as core dataclasses, plus the authoring metadata the tests check it against.

    Two return values on purpose. `Exercise` carries exactly the four fields the design model
    names, and difficulty is deliberately absent from it (v2.8 A4a) -- it is computed from the
    shortest proof, never stored. `expected_entailment` and `expected_merges` are the AUTHOR'S
    CLAIMS about an exercise, checked by `test_bank.py` against what the pipeline computes; core
    must never see them, or a wrong claim would become the answer.
    """
    path = BANK_PATH if path is None else path
    rows = _read(path, config.BANK_SCHEMA_VERSION, BankError).get("exercises")
    if not isinstance(rows, list) or not rows:
        raise BankError(f"{path}: `exercises` must be a non-empty list")

    seen: set[str] = set()
    exercises, meta = [], {}
    for row in rows:
        for field in ("id", "topic", "paragraph", "conclusion", "expected_entailment"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise BankError(f"{path}: exercise {row.get('id')!r} has no {field}")
        if row["id"] in seen:
            raise BankError(f"{path}: duplicate exercise id {row['id']!r}")
        if row["expected_entailment"] not in ("entails", "does_not_follow"):
            raise BankError(
                f"{path}: {row['id']}: expected_entailment is {row['expected_entailment']!r}"
            )
        merges = row.get("expected_merges", [])
        if not isinstance(merges, list) or any(
            not isinstance(pair, list) or len(pair) != 2 for pair in merges
        ):
            raise BankError(f"{path}: {row['id']}: expected_merges must be a list of pairs")
        seen.add(row["id"])
        exercises.append(Exercise(row["id"], row["paragraph"], row["conclusion"], row["topic"]))
        meta[row["id"]] = {
            "expected_entailment": row["expected_entailment"],
            "expected_merges": [tuple(pair) for pair in merges],
            "covers": tuple(row.get("covers", ())),
        }
    return tuple(exercises), meta


def load_bands(path: Path | None = None) -> dict[str, str]:
    """Difficulty bands, DERIVED by scripts/difficulty.py and never hand-written.

    A missing file is a named error rather than an empty mapping: `next_exercise` degrades
    gracefully on an unbanded exercise, so an empty mapping would silently turn band selection
    off for the whole bank instead of saying the derived data had not been generated.
    """
    path = BANDS_PATH if path is None else path
    bands = _read(path, config.BANK_SCHEMA_VERSION, BankError).get("bands")
    if not isinstance(bands, dict) or not all(
        isinstance(k, str) and v in ("short", "medium", "long") for k, v in bands.items()
    ):
        raise BankError(f"{path}: `bands` must map exercise id to short|medium|long")
    return dict(bands)


class MessageError(DataError):
    """Raised when `data/messages.yaml` is missing a code the system can produce."""


def load_messages(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Every user-facing template, validated against the enums that can produce one.

    Checked at startup for the same reason the policy table is: the edge looks a code up with no
    default, because a default would show a student generic text for a specific mistake, and
    naming the mistake is the whole point. A missing template is therefore a crash in front of a
    student unless it is caught here.
    """
    path = MESSAGES_PATH if path is None else path
    raw = _read(path, config.MESSAGES_SCHEMA_VERSION, MessageError, text=True)
    sections = {name: table for name, table in raw.items() if isinstance(table, dict)}
    for group, wanted in required_messages().items():
        if missing := wanted - set(sections.get(group, {})):
            raise MessageError(f"{path}: {group} has no template for {sorted(missing)}")
    for group, table in sections.items():
        for key, text in table.items():
            if not isinstance(text, str) or not text.strip():
                raise MessageError(f"{path}: {group}.{key} is not a non-empty string")
            _check_placeholders(path, group, key, text)
    # Vice versa: a placeholder the renderer goes to the trouble of supplying and that no template
    # uses is either a dead argument or a template someone forgot to finish.
    for group, supplied in SUPPLIED.items():
        used = {name for text in sections.get(group, {}).values() for name in _fields(text)}
        if unused := supplied - used:
            raise MessageError(f"{path}: {group} templates never use {sorted(unused)}")
    return sections


# Which `{placeholders}` the renderer supplies, per group. This is the CONTRACT between
# `messages.yaml` and `app/render.py`, and it is checked in both directions at startup: a
# template using an unknown name is a KeyError in front of a student, and a supplied name no
# template uses is a dead argument or an unfinished template.
SUPPLIED = {
    "step": {"missing", "extra"},
    "productivity": set(),
    "hint": {"clauses", "resolvent"},
    "claim": set(),
    "error": {"sentence"},
    "entailment": {"row"},
    "warning": {"phrase"},
    "cli": {"exercise", "topic", "band", "commands", "sentence"},
}


def _fields(text: str) -> set[str]:
    """The `{placeholder}` names in a template, parsed by the formatter itself.

    `string.Formatter`, not a regex: it is the thing that will actually do the substitution, so it
    agrees with `str.format` about escaping by construction.
    """
    from string import Formatter

    return {name for _, name, _, _ in Formatter().parse(text) if name}


def _check_placeholders(path: Path, group: str, key: str, text: str) -> None:
    if group not in SUPPLIED:
        return  # a group with no renderer contract carries no placeholders to check
    if unknown := _fields(text) - SUPPLIED[group]:
        raise MessageError(
            f"{path}: {group}.{key} uses {sorted(unknown)}, which the renderer does not supply; "
            f"it supplies {sorted(SUPPLIED[group]) or 'nothing'}"
        )


def required_messages() -> dict[str, set[str]]:
    """Which templates must exist, derived from the enums rather than from the file.

    Deriving it from `messages.yaml` would make the check agree with the file by construction --
    the same mistake the policy check avoids.
    """
    return {
        "step": {code.value for code in Code},
        "productivity": {"productive", "unproductive", "unknown"},
        "hint": {f"HINT_{n}" for n in (1, 2, 3)}
        | {f"HINT_NOT_FOLLOW_{n}" for n in (1, 2, 3)}
        | {"HINT_FALLBACK", "HINT_UNAVAILABLE"},
        "claim": {"CLAIM_ACCEPTED", "CLAIM_REJECTED"},
        "error": {code.value for code in ErrorCode},
        "entailment": {v.name for v in Verdict} | {"counterexample"},
        # The adapter's own chrome. Listed so `cli.py` cannot acquire a sentence of its own:
        # every string it prints is one of these keys (sprint item 1).
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
        },
    }
