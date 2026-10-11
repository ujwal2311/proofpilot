"""The display model: one board, built once, used by both the CLI and the API.

Core speaks in clause SETS -- `frozenset[frozenset[str]]`. A student speaks in clause NAMES: "c1",
"c2". Something has to assign and keep those names, and that something must not be core, because
a name is a presentation concern and core has no business holding one.

It must also not be two somethings. The CLI and the API would each have invented their own
numbering, and the ids in a saved session would then depend on which client wrote it -- a bug that
only appears when a student opens the browser after using the CLI, which is to say in front of the
examiner.

So: `Board` owns the mapping, in one place. It is append-only and insertion-ordered, which is what
makes an id stable for the lifetime of an exercise.
"""

from dataclasses import dataclass, field

from src.core.logic import Clause
from src.core.session import Analysis


@dataclass
class Board:
    """The clauses on screen, their ids, and which of them the conclusion can reach.

    Deliberately NOT frozen, and deliberately not a `State`. It is the one mutable thing in the
    edge, because a board grows as a student derives clauses -- and keeping it out of `State`
    means `session.py` remains the only writer of the session itself (v2.11).
    """

    named: dict[str, Clause] = field(default_factory=dict)
    relevant: set[str] = field(default_factory=set)

    @classmethod
    def of(cls, found: Analysis) -> "Board":
        """Lay out a freshly analysed exercise: premises first, then the negated goal."""
        board = cls()
        kept = set(found.relevance.kept) if found.relevance else set()
        goal = set(found.goal)
        for clause in [*found.kb, *found.goal]:
            name = board.add(clause)
            if clause in kept or clause in goal:
                board.relevant.add(name)
        return board

    def add(self, clause: Clause) -> str:
        """Give a clause the next id, or return the id it already has.

        Ids never move and never repeat: `c4` means the same clause for the whole exercise, so a
        hint that says "resolve c1, c2" is still true after the board grows.
        """
        for name, existing in self.named.items():
            if existing == clause:
                return name
        name = f"c{len(self.named) + 1}"
        self.named[name] = clause
        return name

    def clauses(self) -> frozenset[Clause]:
        """What core wants: the set, with the names thrown away."""
        return frozenset(self.named.values())

    def names(self) -> dict[Clause, str]:
        """The reverse map, for rendering a hint that core expressed as clauses."""
        return {clause: name for name, clause in self.named.items()}

    def __getitem__(self, name: str) -> Clause:
        return self.named[name]

    def __contains__(self, name: object) -> bool:
        return name in self.named
