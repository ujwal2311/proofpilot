"""Bayesian Knowledge Tracing: one skill, one observation at a time (docs/HLD.md section 6.8).

    P'_correct = P(1-s) / [P(1-s) + (1-P)g]
    P'_wrong   = P s     / [P s     + (1-P)(1-g)]
    P_next     = P' + (1-P') T

This module owns the arithmetic and the parameter validation and nothing else (section 4.1). It
does not know which skills an action observes -- that is `tutor.py` reading the policy table --
and keeping the split is what lets the maths be checked by hand against section 17.7 with no
tutoring context at all.

The posterior and the learning step are separate functions on purpose. Folding T into the Bayes
step is the classic BKT implementation error, and it produces plausible-looking numbers; keeping
them apart means the intermediate value the design review computed (0.6585366) is directly
assertable instead of being hidden inside a composite.
"""

from dataclasses import dataclass

from src.core import config
from src.core.models import Skill


class ParameterError(ValueError):
    """Raised when a BKT parameter is outside its permitted range.

    A named error rather than an assert: these values arrive from `config.py` and, in the
    simulation, from a sweep, so a bad one is an input to validate at the boundary rather than an
    internal invariant to trust (CLAUDE.md rule 5).
    """


@dataclass(frozen=True)
class BktParams:
    """The four BKT parameters plus the mastery threshold, validated on construction.

    Frozen because a parameter set is a configuration, not a state: the simulation builds several
    and compares them, and a shared mutable one would let a sweep contaminate the run after it.
    """

    p0: float
    guess: float
    slip: float
    transit: float
    threshold: float

    def __post_init__(self) -> None:
        for name in ("p0", "guess", "slip", "transit", "threshold"):
            value = getattr(self, name)
            if not 0.0 < value < 1.0:
                raise ParameterError(f"{name} must be strictly between 0 and 1, got {value}")
        # g + s >= 1 makes the model perverse: a wrong answer would then be MORE likely from a
        # student who has mastered the skill than from one who has not, so every update would run
        # backwards while still producing numbers in range. Required by name in section 6.8.
        if self.guess + self.slip >= 1.0:
            raise ParameterError(f"guess + slip must be below 1, got {self.guess} + {self.slip}")

    @classmethod
    def from_config(cls) -> "BktParams":
        """The shipped parameters. Every number lives in `config.py` and nowhere else (rule 11)."""
        return cls(
            p0=config.BKT_P0,
            guess=config.BKT_GUESS,
            slip=config.BKT_SLIP,
            transit=config.BKT_TRANSIT,
            threshold=config.MASTERY_THRESHOLD,
        )


def posterior(p: float, correct: bool, params: BktParams) -> float:
    """P' -- belief after ONE observation, by Bayes. No learning step; see `update`.

    The denominators are strictly positive whenever 0 < g, s, P < 1, which `BktParams` enforces,
    so there is no division-by-zero branch to write or to test (section 17.7).
    """
    if correct:
        evidence = p * (1 - params.slip)
        return evidence / (evidence + (1 - p) * params.guess)
    evidence = p * params.slip
    return evidence / (evidence + (1 - p) * (1 - params.guess))


def update(p: float, correct: bool, params: BktParams) -> float:
    """P_next -- the posterior plus the chance of having learned from this opportunity.

    The transit term pulls upward even after a wrong answer, so mastery converges to a floor
    rather than to zero: a struggling student is never written off as unable to improve.

    The result is clamped strictly inside (0, 1). The model never reaches either bound, but
    float64 does: MEASURED, 23 consecutive correct answers drive P to exactly 1.0, and from there
    `posterior(1.0, wrong)` is also 1.0, so the skill freezes and the tutor keeps asserting
    mastery that later evidence contradicts. The clamp restores the 0 < P < 1 precondition
    section 17.7 argues from; its SIZE is derived from the slip rule in `config.py`, so the
    ceiling is the point from which two wrong answers are forgiven and a third is not.
    """
    after = posterior(p, correct, params)
    moved = after + (1 - after) * params.transit
    return min(max(moved, config.MASTERY_SLACK), 1.0 - config.MASTERY_SLACK)


def is_done(mastery: dict[Skill, float], params: BktParams) -> bool:
    """Is every ACTIVE skill at or above the threshold?

    Only the skills present are judged, because M1 has three active and M2 four -- requiring
    TRANSLATE in M1 would make the set unfinishable. An EMPTY mapping is not done: `all()` is
    true of nothing, which would mark a student finished before they had started.
    """
    return bool(mastery) and all(value >= params.threshold for value in mastery.values())
