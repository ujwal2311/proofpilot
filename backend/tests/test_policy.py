"""Tests for data/policy.yaml -- the evidence mapping as declarative policy data (v2.10 item 2).

Written before `tutor.py` exists, deliberately: these tests define the contract 6b must satisfy.

CONTRACT. The table is DATA, loaded and schema-validated at the EDGE (v2.4) and handed to core as
a plain mapping. Two properties have to hold, and only one of them is a schema check:

  1. SHAPE -- every row names every skill, and every value is exactly `right`, `wrong` or null.
     `null` means NO UPDATE; it is not a default and not "wrong".
  2. TOTALITY -- the full product of trigger x hint_used x mode resolves to a defined entry, so
     no consumer has a `KeyError` path. The trigger set is cross-checked against `logic.Code`,
     which is what stops a new diagnosis code being added without a row.

The hint rule is a uniform TRANSFORM over the table, not extra rows (HLD section 9). It is
implemented here as an independent reference so that 6b's `tutor.py` has something to disagree
with: a transform written once in the implementation and never anywhere else is a transform
nobody has checked.
"""

from itertools import product
from pathlib import Path

import pytest
import yaml
from src.core.logic import Code
from src.core.models import Skill

POLICY = Path(__file__).resolve().parents[2] / "data" / "policy.yaml"
LEGAL_VALUES = {"right", "wrong", None}
MODES = ("practice", "own_question")

# The non-`step` triggers. Written out rather than derived, because the point of the totality
# check is to compare two independently written lists -- deriving this one from the file would
# make the test agree with the file by construction.
VALID_SPLITS = ("productive", "unproductive", "unknown")
OTHER_TRIGGERS = (
    "claim_not_provable.CLAIM_ACCEPTED",
    "claim_not_provable.CLAIM_REJECTED",
    "translate.CORRECT",
    "translate.CORRECT_CONTRAPOSITIVE",
    "translate.ERROR",
    "parse_failure",
    "merge",
    "hint",
)
SCORING_TRIGGERS = ("step.", "claim_not_provable.")  # the only actions the hint rule touches


@pytest.fixture(scope="module")
def policy() -> dict:
    return yaml.safe_load(POLICY.read_text(encoding="utf-8"))


def _expected_triggers() -> set[str]:
    steps = {f"step.{code.value}" for code in Code if code is not Code.VALID}
    steps |= {f"step.VALID.{split}" for split in VALID_SPLITS}
    return steps | set(OTHER_TRIGGERS)


def _apply_hint_rule(row: dict[str, str | None], hinted: bool) -> dict[str, str | None]:
    """HLD section 9: a hint turns every skill that WOULD be observed into `wrong`.

    Rows that are null stay null -- a hint must never create an observation that was not already
    there, or asking for help would start scoring skills the action never tested.
    """
    if not hinted:
        return row
    return {skill: ("wrong" if value is not None else None) for skill, value in row.items()}


# ------------------------------------------------------------------------------------------ shape


def test_the_file_parses_and_declares_its_schema_version(policy: dict) -> None:
    assert policy["schema_version"] == 1
    assert isinstance(policy["evidence"], dict)


def test_every_row_names_every_skill_with_a_legal_value(policy: dict) -> None:
    for trigger, row in policy["evidence"].items():
        assert set(row) == {skill.value for skill in Skill}, f"{trigger}: wrong skill set"
        for skill, value in row.items():
            assert value in LEGAL_VALUES, f"{trigger}.{skill} = {value!r} is not right/wrong/null"


def test_no_row_is_entirely_absent_of_meaning(policy: dict) -> None:
    # An all-null row is legitimate for the three non-evidence triggers and nowhere else: a
    # scoring action that observed nothing would be a silently dead code path.
    silent = {t for t, row in policy["evidence"].items() if set(row.values()) == {None}}
    assert silent == {"parse_failure", "merge", "hint"}


# --------------------------------------------------------------------------------------- totality


def test_policy_covers_every_diagnosis_code(policy: dict) -> None:
    # The cross-check that makes a KeyError unreachable. `logic.Code` is the authority on what a
    # step can produce, so a seventh diagnosis code added without a policy row fails here rather
    # than at runtime in front of a student.
    missing = _expected_triggers() - set(policy["evidence"])
    extra = set(policy["evidence"]) - _expected_triggers()
    assert not missing, f"no evidence row for {sorted(missing)}"
    assert not extra, f"evidence rows for triggers nothing can produce: {sorted(extra)}"


def test_the_full_product_of_trigger_hint_and_mode_resolves(policy: dict) -> None:
    # TOTALITY, stated as the product the student asked for: every combination maps to a defined
    # entry, with no default and no fallback.
    resolved = 0
    for trigger, hinted, mode in product(sorted(_expected_triggers()), (False, True), MODES):
        row = policy["evidence"][trigger]  # must not KeyError for any trigger
        observed = _apply_hint_rule(row, hinted)
        assert set(observed) == {skill.value for skill in Skill}
        for value in observed.values():
            assert value in LEGAL_VALUES
        assert mode in MODES  # mode never changes a row; asserted so the claim is not implicit
        resolved += 1
    # 16 triggers x 2 hint states x 2 modes. The literal is spelled out because the first version
    # of this test asserted 68 from a miscount of the trigger list, and a total nobody has
    # computed by hand is a total that cannot catch a missing row.
    assert len(_expected_triggers()) == 16
    assert resolved == 16 * 2 * len(MODES) == 64


def test_mode_never_changes_an_observation(policy: dict) -> None:
    # The one place a reader might expect a difference. Per OQ2 parse failures are not evidence in
    # EITHER mode, and no other row differs by mode either.
    #
    # A structural check, not a grep: the first version searched the file text for "mode" and
    # failed on the comment that explains this very property. A mode split could only be
    # expressed as a nested mapping under a skill, or as a mode-qualified trigger name.
    for trigger, row in policy["evidence"].items():
        for skill, value in row.items():
            assert not isinstance(value, dict), f"{trigger}.{skill} branches on something"
        for mode in MODES:
            assert not trigger.endswith(f".{mode}"), f"{trigger} is mode-qualified"


# --------------------------------------------------------------------------------- the hint rule


def test_a_hint_turns_every_observation_wrong(policy: dict) -> None:
    row = policy["evidence"]["step.VALID.productive"]
    assert set(row.values()) == {"right", None}
    hinted = _apply_hint_rule(row, True)
    assert hinted[Skill.CLASH.value] == "wrong"
    assert hinted[Skill.STRATEGY.value] == "wrong"


def test_a_hint_never_creates_an_observation_that_was_not_there(policy: dict) -> None:
    # The half of the rule that is easy to get wrong: nulls must survive. Without this, asking for
    # a hint would score TRANSLATE on a proof step that never involved translating anything.
    for trigger, row in policy["evidence"].items():
        hinted = _apply_hint_rule(row, True)
        for skill, value in row.items():
            if value is None:
                assert hinted[skill] is None, f"{trigger}.{skill} was invented by the hint rule"


def test_a_hinted_accepted_claim_scores_strategy_wrong(policy: dict) -> None:
    # The row the HLD spells out explicitly (section 9, section 6.6.1): escalating the
    # "it doesn't follow" ladder to level 3 and then clicking it is STRATEGY-wrong even though
    # the claim itself is accepted. It falls out of the uniform rule rather than needing its own
    # row, and this test is what proves that.
    accepted = policy["evidence"]["claim_not_provable.CLAIM_ACCEPTED"]
    assert accepted[Skill.STRATEGY.value] == "right"
    assert _apply_hint_rule(accepted, True)[Skill.STRATEGY.value] == "wrong"


def test_the_hint_action_itself_is_never_evidence(policy: dict) -> None:
    assert set(policy["evidence"]["hint"].values()) == {None}
    assert set(_apply_hint_rule(policy["evidence"]["hint"], True).values()) == {None}
