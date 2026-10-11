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

from pathlib import Path

import yaml

from src.core import config
from src.core.logic import Code
from src.core.models import Skill

DATA = Path(__file__).resolve().parents[2] / "data"
POLICY_PATH = DATA / "policy.yaml"

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


class PolicyError(ValueError):
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
    if not path.is_file():
        raise PolicyError(f"policy file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as problem:
        raise PolicyError(f"{path} is not valid YAML: {problem}") from problem

    want = config.POLICY_SCHEMA_VERSION  # rule 11: the number lives in config.py, not in a message
    found = raw.get("schema_version") if isinstance(raw, dict) else type(raw).__name__
    _require(found == want, path, f"schema_version must be {want}, got {found}")

    table = raw.get("evidence") if isinstance(raw, dict) else None
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
