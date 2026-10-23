"""Turn the finished, already-checked board into a concise proof trace."""

from src.core.models import ClauseRec


def _clause_text(clause: ClauseRec) -> str:
    if not clause.literals:
        return "the empty clause"
    return " or ".join(clause.literals)


def narrate(clauses: tuple[ClauseRec, ...]) -> tuple[str, ...]:
    """Describe each board clause in order without rechecking its validity.

    Resolution diagnosis belongs to ``logic.py`` and the clause list is already
    the verified session trace. This module only explains that trace, so it
    cannot make a second proof judgment that diverges from the board.
    """
    lines = []
    for clause in clauses:
        text = _clause_text(clause)
        if clause.origin == "given":
            source = f" from {clause.source_sentence_id}" if clause.source_sentence_id else ""
            lines.append(f"{clause.id} is the given clause{source}: {text}.")
        elif clause.origin == "goal":
            lines.append(f"{clause.id} is the negated conclusion: {text}.")
        else:
            lines.append(f"{clause.id} is derived: {text}.")
    return tuple(lines)
