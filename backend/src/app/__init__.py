"""The shared edge. Everything the CLI and the API both need, exactly once.

The split, and the reason for it:

    core/        pure Python. Decides everything. Reads no file, holds no wording, no ids.
    app/         the shared edge. Loads and validates the data files at startup, prepares text,
                 renders a code into words, and owns the board's clause ids.
    cli.py       a thin I/O adapter: read a line, call app, print.
    api/main.py  a thin HTTP adapter: parse a body, call app, return JSON.

**Both adapters are I/O only.** No decisions, no wording. Enforced, not promised:
`test_adapters_hold_no_user_facing_wording` parses `cli.py` and `api/*.py` and fails on any string
constant that reads like a sentence to a student. Without that, wording creeps back one convenient
f-string at a time, and the student's experience starts depending on which client they used.

`Runtime.load()` is the startup check. Every data file is validated **before** a student can reach
it, with a named error per failure mode: a policy table missing a trigger, a message table missing
a code or using a placeholder nobody supplies, a bank whose entailment claim is wrong. The
alternative is a `KeyError` mid-session on whichever path happens to be unlucky, and the honest
place to fail is at boot.
"""

from dataclasses import dataclass

from src.app.data import load_bands, load_bank, load_messages, load_policy
from src.app.render import Renderer
from src.core import session
from src.core.bkt import BktParams
from src.core.models import Exercise, MergeChoice, Skill
from src.core.session import Analysis

M1_SKILLS = (Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY)


@dataclass(frozen=True)
class Runtime:
    """Everything loaded and validated once, at startup, for the whole process."""

    policy: dict[str, dict[str, str | None]]
    render: Renderer
    bank: tuple[Exercise, ...]
    bands: dict[str, str]
    params: BktParams

    @classmethod
    def load(cls) -> "Runtime":
        """Load and validate every data file. Raises a named error rather than starting broken."""
        return cls(
            policy=load_policy(),
            render=Renderer(load_messages()),
            bank=load_bank()[0],
            bands=load_bands(),
            params=BktParams.from_config(),
        )

    def fresh_mastery(self) -> dict[Skill, float]:
        """A new student: the prior in every M1 skill. TRANSLATE joins in M2."""
        return dict.fromkeys(M1_SKILLS, self.params.p0)


def prepare(paragraph: str, conclusion: str, merges: tuple[MergeChoice, ...] = ()) -> Analysis:
    """THE text entry point for every adapter. Normalizes and runs the section 7 pipeline.

    A one-line pass-through to `core.session.analyse`, and that is the point: it gives every
    adapter exactly one name to call, so no adapter can reach past it and normalize differently.
    The bug this closes already happened once -- the conclusion was prepared by a different path
    from the paragraph, so a trailing full stop made "we get wet." and "we get wet" two facts and
    the worked example stopped entailing. `test_normalisation.py` feeds every entry point the same
    messy input and asserts the same answer.
    """
    return session.analyse(paragraph, conclusion, merges)
