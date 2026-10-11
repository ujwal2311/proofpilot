"""Refuse an incoming session that is well-formed but impossible (HLD section 8).

`api/schemas.py` settles STRUCTURE -- fields present, types right, nested records well-formed.
What is left is the list section 8 actually names, and every one of them describes a body that
could not have come from a real session: an unknown clause id, a symbol from no fact in this
exercise, more clauses or literals than the limits allow, a mastery value outside the open unit
interval the BKT model is defined on.

None of them is a wrong ANSWER, so none is teaching content: they are 400s, not 200s with a code.
That is the whole rule section 8 states, and it is why these messages are not in `messages.yaml` --
they are read by a client developer looking at a rejected request, never by a student.

It lives in `app/` rather than in the API because validating what arrived from outside is what
`app/` already does for the data files, and because `cli.py` and `api/main.py` are I/O only --
`test_adapters_hold_no_user_facing_wording` flagged these three messages the moment they were
written inside the adapter, which is the guard doing exactly its job.
"""

from src.core import config
from src.core.models import State


class Tampered(ValueError):
    """A session that is structurally valid but cannot have come from this system."""


def audit(state: State) -> None:
    """Refuse a session that is well-formed but impossible (section 8).

    Structure is already settled by `schemas.load_state`: fields present, types right, nested
    records well-formed. What is left is the list section 8 actually names, and every one of these
    describes a body that could not have come from a real session.

    None of them is a wrong ANSWER, so none is teaching content: they are 400s, not 200s with a
    code. That is the whole rule section 8 states.

    Two halves, because one function doing both scored 11 on the complexity gate: the BOARD, and
    the student's PROGRESS.
    """
    _audit_board(state)
    _audit_progress(state)


def _audit_board(state: State) -> None:
    """The clauses: how many, named how, over what vocabulary."""
    if len(state.clauses) > config.MAX_BOARD_CLAUSES:
        raise Tampered(f"{len(state.clauses)} clauses")
    ids = [record.id for record in state.clauses]
    if len(set(ids)) != len(ids):
        raise Tampered(f"duplicate clause id in {ids}")
    for record in state.clauses:
        if len(record.literals) > config.MAX_CLAUSE_LITERALS:
            raise Tampered(f"{record.id} has {len(record.literals)} literals")
    if missing := set(state.relevant_ids) - set(ids):
        raise Tampered(f"relevant_ids names {sorted(missing)}, which is not on the board")

    # A symbol from no fact in this exercise. The facts ARE the exercise's vocabulary, so a
    # literal outside them means the board was edited rather than derived. Skipped when there are
    # no facts at all, which is a session that has not been parsed yet rather than a tampered one.
    known = {fact.symbol for fact in state.facts}
    foreign = {
        literal.lstrip("~")
        for record in state.clauses
        for literal in record.literals
        if literal.lstrip("~") not in known
    }
    if known and foreign:
        raise Tampered(f"symbols {sorted(foreign)} belong to no fact in this exercise")


def _audit_progress(state: State) -> None:
    """Mastery and the hint level: the two numbers a client could edit to its advantage."""
    for skill, value in state.mastery.items():
        if not 0.0 < value < 1.0:
            raise Tampered(f"mastery {skill.value}={value} is outside (0,1)")
    if not 0 <= state.hint_level <= 3:
        raise Tampered(f"hint_level {state.hint_level}")
