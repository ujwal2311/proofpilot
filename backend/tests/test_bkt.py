"""Tests for core.bkt -- the single-skill Bayesian update (docs/HLD.md sections 6.8, 17.7).

Written before the implementation.

CONTRACT. `bkt.py` owns the arithmetic and the parameter validation, and nothing else (section
4.1). It must not know which skills an action observes -- that is `tutor.py`, and keeping the
split means the maths can be checked by hand against the HLD without any tutoring context.

  posterior(p, correct, params) -> P' after one observation, Bayes only, no learning step
  update(p, correct, params)    -> P_next = P' + (1 - P') * T
  is_done(mastery, params)      -> every ACTIVE skill at or above the threshold
  BktParams                     -> validates 0 < g,s,T,P0 < 1 and g + s < 1, by name

The hand example in section 17.7 is the anchor: P=0.3, g=0.2, s=0.1, T=0.15 gives 0.7098 for a
correct answer and 0.1932 for a wrong one. Those two numbers are checked to four decimals because
they were computed independently in the design review, so they catch a rearranged formula that a
self-consistent implementation would never notice.
"""

import copy
from dataclasses import FrozenInstanceError

import pytest
from src.core import config
from src.core.bkt import BktParams, ParameterError, is_done, posterior, update
from src.core.models import Skill

HLD = BktParams(p0=0.3, guess=0.2, slip=0.1, transit=0.15, threshold=0.95)


# ------------------------------------------------------------------- the section 17.7 hand example


def test_the_hand_example_from_the_design_review() -> None:
    # Correct: P' = 0.3*0.9 / (0.3*0.9 + 0.7*0.2) = 0.27/0.41 = 0.6585366
    #          P_next = 0.6585366 + 0.3414634*0.15 = 0.7097561 -> 0.7098
    assert round(update(0.3, True, HLD), 4) == 0.7098
    # Wrong:   P' = 0.3*0.1 / (0.3*0.1 + 0.7*0.8) = 0.03/0.59 = 0.0508475
    #          P_next = 0.0508475 + 0.9491525*0.15 = 0.1932203 -> 0.1932
    assert round(update(0.3, False, HLD), 4) == 0.1932


def test_the_posterior_is_separable_from_the_learning_step() -> None:
    # Checked separately so a formula that folds T into the Bayes step cannot pass by cancelling
    # its own error. These are the intermediate values the HLD prints.
    assert round(posterior(0.3, True, HLD), 7) == 0.6585366
    assert round(posterior(0.3, False, HLD), 7) == 0.0508475


def test_update_is_the_posterior_plus_the_transit_term() -> None:
    for p in (0.05, 0.3, 0.5, 0.87):
        for correct in (True, False):
            after = posterior(p, correct, HLD)
            assert update(p, correct, HLD) == pytest.approx(after + (1 - after) * HLD.transit)


# --------------------------------------------------------------------------------- the arithmetic


@pytest.mark.parametrize("p", [0.01, 0.1, 0.3, 0.5, 0.75, 0.99])
def test_a_correct_answer_raises_mastery_and_a_wrong_one_lowers_the_posterior(p: float) -> None:
    # The direction of the update is the whole point of the model, and it is the one thing a
    # swapped guess/slip would break while still producing plausible-looking numbers.
    assert posterior(p, True, HLD) > p
    assert posterior(p, False, HLD) < p


@pytest.mark.parametrize("p", [0.01, 0.3, 0.5, 0.99])
def test_mastery_stays_inside_the_open_unit_interval(p: float) -> None:
    # A probability that reaches 0 or 1 can never move again, so the model would be stuck. With
    # 0 < g,s,T,P < 1 the denominators are strictly positive and no clamping branch is needed.
    for correct in (True, False):
        assert 0.0 < update(p, correct, HLD) < 1.0


def test_a_long_run_of_correct_answers_converges_upward_and_monotonically() -> None:
    p, seen = HLD.p0, []
    for _ in range(40):
        p = update(p, True, HLD)
        seen.append(p)
    assert seen == sorted(seen), "mastery must never fall on a correct answer"
    assert seen[-1] > HLD.threshold
    assert seen[-1] < 1.0


def test_mastery_never_saturates_so_a_skill_can_always_move_again() -> None:
    # A REAL DEFECT this test found, not a hypothetical. The model never reaches 1, but float64
    # does: 23 consecutive correct answers drove P to exactly 1.0, and `posterior(1.0, wrong)` is
    # 1.0 * s / (1.0 * s + 0) = 1.0 -- so the skill froze and the tutor would have gone on
    # asserting mastery that every later wrong answer contradicted.
    p = HLD.p0
    for _ in range(200):
        p = update(p, True, HLD)
    assert p < 1.0, "mastery saturated; a frozen skill can never be lost"
    assert p == 1.0 - config.MASTERY_EPSILON

    # Recovery must be possible in a realistic number of attempts, or the clamp would only move
    # the problem rather than fix it.
    wrong = 0
    while p >= HLD.threshold:
        p = update(p, False, HLD)
        wrong += 1
        assert wrong < 50, "a mastered skill could not be lost in any reasonable run"
    assert wrong <= 15, f"took {wrong} wrong answers to fall below the threshold"


def test_the_clamp_does_not_disturb_the_hand_example() -> None:
    # The guard must be invisible anywhere near the working range. If it showed up in the
    # section 17.7 figures it would be changing the model, not protecting it.
    assert round(update(0.3, True, HLD), 4) == 0.7098
    assert round(update(0.3, False, HLD), 4) == 0.1932
    assert (
        update(0.3, True, HLD)
        == posterior(0.3, True, HLD) + (1 - posterior(0.3, True, HLD)) * HLD.transit
    )


def test_a_long_run_of_wrong_answers_stays_above_zero() -> None:
    # The transit term means a student is never written off entirely: T pulls upward even on a
    # wrong answer, so mastery converges to a floor rather than to zero.
    p = HLD.p0
    for _ in range(40):
        p = update(p, False, HLD)
    assert 0.0 < p < HLD.p0


# ------------------------------------------------------------------------------------ validation


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("guess", 0.0),
        ("guess", 1.0),
        ("slip", 0.0),
        ("slip", 1.0),
        ("transit", 0.0),
        ("transit", 1.0),
        ("p0", 0.0),
        ("p0", 1.0),
        ("guess", -0.1),
        ("slip", 1.5),
    ],
)
def test_a_parameter_outside_the_open_unit_interval_is_refused(field: str, value: float) -> None:
    with pytest.raises(ParameterError, match=field):
        BktParams(**{**vars(HLD), field: value})


def test_guess_plus_slip_must_be_below_one() -> None:
    # g + s >= 1 makes the model perverse: a wrong answer would be more likely from a student who
    # HAS mastered the skill than from one who has not, so the update would run backwards. The
    # HLD requires this check by name (section 6.8).
    with pytest.raises(ParameterError, match="guess"):
        BktParams(p0=0.3, guess=0.6, slip=0.4, transit=0.15, threshold=0.95)
    BktParams(p0=0.3, guess=0.55, slip=0.44, transit=0.15, threshold=0.95)  # 0.99 < 1 is fine


def test_a_threshold_outside_the_open_unit_interval_is_refused() -> None:
    with pytest.raises(ParameterError, match="threshold"):
        BktParams(p0=0.3, guess=0.2, slip=0.1, transit=0.15, threshold=1.0)


def test_the_configured_defaults_are_valid() -> None:
    # config.py is the single source for every number (rule 11), so the shipped values must pass
    # the same validation as any hand-built set -- a default that failed its own check would be
    # discovered by a student, at runtime.
    assert BktParams.from_config() == HLD


# --------------------------------------------------------------------------------------- is_done


def test_is_done_requires_every_active_skill_to_reach_the_threshold() -> None:
    at = HLD.threshold
    assert is_done({Skill.CLASH: at, Skill.RESOLVE: at, Skill.STRATEGY: at}, HLD)
    assert not is_done({Skill.CLASH: at, Skill.RESOLVE: at, Skill.STRATEGY: at - 0.001}, HLD)


def test_is_done_is_at_or_above_the_threshold_not_strictly_above() -> None:
    # The HLD writes ">= mastery_threshold" (section 9). Off by one strictness here would make
    # the exercise set unfinishable in the one case that matters -- landing exactly on the mark.
    assert is_done({Skill.CLASH: HLD.threshold}, HLD)


def test_is_done_judges_only_the_skills_it_is_given() -> None:
    # M1 has three active skills and M2 four; TRANSLATE must not be required in M1, and an empty
    # dict must not read as "done" -- that would mark a student finished before they started.
    assert is_done({Skill.CLASH: 1 - 1e-9, Skill.RESOLVE: 0.99, Skill.STRATEGY: 0.96}, HLD)
    assert not is_done({}, HLD)


# ---------------------------------------------------------------------------------------- purity


def test_no_function_mutates_its_inputs() -> None:
    # Core is pure (HLD 4). The API replays a student's merges and actions over a stored state, so
    # a function that mutated its argument would corrupt the caller's copy silently.
    mastery = {Skill.CLASH: 0.3, Skill.RESOLVE: 0.4, Skill.STRATEGY: 0.5}
    params = BktParams.from_config()
    before_mastery, before_params = copy.deepcopy(mastery), copy.deepcopy(params)

    posterior(0.3, True, params)
    update(0.3, False, params)
    is_done(mastery, params)

    assert mastery == before_mastery
    assert params == before_params


def test_the_parameters_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        HLD.guess = 0.9  # type: ignore[misc]


def test_the_configured_parameters_are_documented_as_assumed() -> None:
    # The HLD and the README both state that these are ASSUMED, not fitted (section 6.8). A
    # number presented as measured when it was chosen would be a false claim in the report, so
    # the word has to be where the number is.
    source = (config.__file__ or "").replace("\\", "/")
    text = open(source, encoding="utf-8").read()
    assert "ASSUMED" in text, "config.py must say so where the BKT numbers are defined"
