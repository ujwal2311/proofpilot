"""Tests for backend/src/loader.py -- the only module that reads a data file (HLD section 4).

Written before the implementation.

CONTRACT. Core reads no file (v2.4). The edge -- the API, the CLI, a script -- loads every data
file, validates its SHAPE, and hands plain data to core. `loader.py` is that edge, and it owns
nothing else: it validates and stops, with no logic of its own.

This file covers the POLICY loader (sprint F3). The exercises loader lands with the bank in S3 and
the message templates with the API in S4, in this same module.

WHY FAIL-FAST MATTERS HERE. `data/policy.yaml` is the evidence mapping, and `tutor.py` indexes it
by trigger with no default and no fallback -- that is deliberate, because a default would silently
score a skill the action never tested. The cost of that choice is that a malformed or incomplete
policy file is a `KeyError` in front of a student, mid-session, on whichever trigger happens to be
missing. So the file is validated ONCE at startup against `logic.Code`, and a bad file refuses to
start the server. Every broken fixture below is a file that would otherwise have started fine and
failed later.
"""

from pathlib import Path

import pytest
import yaml
from src.core.logic import Code
from src.core.models import Skill
from src.loader import POLICY_PATH, PolicyError, load_policy

SKILLS = [skill.value for skill in Skill]


def _row(**overrides: str | None) -> dict[str, str | None]:
    row: dict[str, str | None] = dict.fromkeys(SKILLS)
    row.update(overrides)
    return row


def _good() -> dict:
    """A minimal policy that is complete by construction, so a fixture breaks ONE thing."""
    real = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    return {"schema_version": real["schema_version"], "evidence": dict(real["evidence"])}


def _write(tmp_path: Path, policy: object) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return path


# ------------------------------------------------------------------------------- the shipped file


def test_the_shipped_policy_loads() -> None:
    policy = load_policy()
    assert set(policy) == set(yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))["evidence"])


def test_the_loader_returns_plain_data_not_objects() -> None:
    # Core takes a plain mapping (v2.10 item 2). A loader that returned a custom type would put
    # an edge import into core's call signature.
    policy = load_policy()
    assert type(policy) is dict
    for trigger, row in policy.items():
        assert type(trigger) is str
        assert type(row) is dict
        assert set(row) == set(SKILLS)
        assert all(value in {"right", "wrong", None} for value in row.values())


def test_the_loader_drops_the_envelope_and_returns_the_table() -> None:
    # `schema_version` is the loader's business, not core's: core receives the table itself, so
    # there is no path where a consumer reads `policy["schema_version"]` as if it were a trigger.
    assert "schema_version" not in load_policy()


def test_loading_twice_gives_equal_but_independent_tables() -> None:
    # The API loads once at startup and passes the table into core on every request. If the
    # loader returned a shared mutable object, one request mutating it would poison the next.
    first, second = load_policy(), load_policy()
    assert first == second
    first["step.NO_CLASH"]["CLASH"] = "right"
    assert load_policy()["step.NO_CLASH"]["CLASH"] == "wrong"


# ------------------------------------------------------------------------------- broken fixtures


def test_a_missing_file_is_a_named_error(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="not found"):
        load_policy(tmp_path / "absent.yaml")


def test_malformed_yaml_is_a_named_error(tmp_path: Path) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text("evidence: [this: is, not: valid\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="not valid YAML"):
        load_policy(path)


def test_an_unsupported_schema_version_is_refused(tmp_path: Path) -> None:
    # The version exists so a shape change is loud. Accepting an unknown one would make it silent,
    # which is the entire failure mode it was added to prevent.
    policy = _good()
    policy["schema_version"] = 99
    with pytest.raises(PolicyError, match="schema_version"):
        load_policy(_write(tmp_path, policy))


def test_a_missing_schema_version_is_refused(tmp_path: Path) -> None:
    policy = _good()
    del policy["schema_version"]
    with pytest.raises(PolicyError, match="schema_version"):
        load_policy(_write(tmp_path, policy))


def test_a_file_without_an_evidence_table_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="evidence"):
        load_policy(_write(tmp_path, {"schema_version": 1}))


def test_an_evidence_table_that_is_not_a_mapping_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="evidence"):
        load_policy(_write(tmp_path, {"schema_version": 1, "evidence": ["step.NO_CLASH"]}))


def test_a_row_missing_a_skill_is_refused(tmp_path: Path) -> None:
    # The realistic edit: a fifth skill is added to the enum and one row is not updated. Without
    # this check, that row scores three skills and silently never observes the fourth.
    policy = _good()
    incomplete = dict(policy["evidence"]["step.NO_CLASH"])
    del incomplete[Skill.TRANSLATE.value]
    policy["evidence"]["step.NO_CLASH"] = incomplete
    with pytest.raises(PolicyError, match="TRANSLATE"):
        load_policy(_write(tmp_path, policy))


def test_a_row_naming_a_skill_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    policy = _good()
    policy["evidence"]["step.NO_CLASH"] = _row(CLASH="wrong", INVENTED="right")
    with pytest.raises(PolicyError, match="INVENTED"):
        load_policy(_write(tmp_path, policy))


def test_a_value_that_is_not_right_wrong_or_null_is_refused(tmp_path: Path) -> None:
    policy = _good()
    policy["evidence"]["step.NO_CLASH"] = _row(CLASH="maybe")
    with pytest.raises(PolicyError, match="maybe"):
        load_policy(_write(tmp_path, policy))


def test_a_value_that_branches_on_something_is_refused(tmp_path: Path) -> None:
    # A nested mapping is how a mode split would have to be written. Mode never changes a row
    # (HLD section 9), so a nested value means the table has grown control flow.
    policy = _good()
    policy["evidence"]["step.NO_CLASH"] = _row(CLASH={"practice": "wrong"})
    with pytest.raises(PolicyError, match="step.NO_CLASH"):
        load_policy(_write(tmp_path, policy))


def test_a_diagnosis_code_with_no_row_is_refused(tmp_path: Path) -> None:
    # THE failure this loader exists for. `logic.Code` is the authority on what a step can
    # produce, so a code with no row is a guaranteed mid-session KeyError -- and it is caught here
    # by comparing against the enum, not against a list copied out of the file.
    policy = _good()
    del policy["evidence"][f"step.{Code.NO_CLASH.value}"]
    with pytest.raises(PolicyError, match="NO_CLASH"):
        load_policy(_write(tmp_path, policy))


def test_a_row_for_a_trigger_nothing_can_produce_is_refused(tmp_path: Path) -> None:
    # The other direction, and not merely tidiness: a row nothing reaches is a rule the team
    # believes is in force when it is dead, which is how a policy decision gets quietly lost.
    policy = _good()
    policy["evidence"]["step.MISSPELLED_CODE"] = _row(CLASH="wrong")
    with pytest.raises(PolicyError, match="MISSPELLED_CODE"):
        load_policy(_write(tmp_path, policy))


def test_an_all_null_scoring_row_is_refused(tmp_path: Path) -> None:
    # Legitimate for exactly three triggers (parse_failure, merge, hint). A SCORING action that
    # observes nothing is a dead feedback path that would look like a working one.
    policy = _good()
    policy["evidence"]["step.NO_CLASH"] = _row()
    with pytest.raises(PolicyError, match="step.NO_CLASH"):
        load_policy(_write(tmp_path, policy))


def test_a_non_evidence_trigger_that_starts_scoring_is_refused(tmp_path: Path) -> None:
    # The reverse of the rule above, and the one that matters pedagogically: parse failures are
    # never evidence in either mode (OQ2). A student refused by the grammar was not assessed, and
    # a row that scored them would punish them for the parser's limits.
    policy = _good()
    policy["evidence"]["parse_failure"] = _row(CLASH="wrong")
    with pytest.raises(PolicyError, match="parse_failure"):
        load_policy(_write(tmp_path, policy))


# --------------------------------------------------------------------------- the guard has teeth


def test_every_broken_fixture_differs_from_a_file_that_loads(tmp_path: Path) -> None:
    # Proof that the fixtures above test the validator and not the YAML parser: the unmodified
    # structure they are all derived from must itself load cleanly.
    assert load_policy(_write(tmp_path, _good())) == load_policy()
