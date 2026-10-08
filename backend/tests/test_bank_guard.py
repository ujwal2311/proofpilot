"""Guard for the exercise bank (docs/HLD.md v2.7 A7).

A bank exercise must never depend on the student noticing and splitting a false merge. The
stemmer deliberately over-merges in a few cases (HLD 3.5), which is safe for a student's own
paragraph because the Facts screen shows both phrases -- but an exercise we ship is different:
if its two distinct phrases collide, every student hits the same confusing screen, and whether
the proof works at all depends on them undoing it.

So: any two distinct phrases in an exercise that share a canonical key must be declared in that
exercise's `expected_merges`. The check is written now and runs against fixtures; it moves to
scripts/ and runs over data/exercises.json when the bank lands in Phase 6.
"""

from itertools import combinations

import pytest
from src.core.facts import canonical_key

# Fixtures stand in for data/exercises.json until it exists. Same shape: the text a student
# reads, plus the merges the author knows the stemmer will make.
FIXTURES = [
    {
        "id": "ex-clean",
        "phrases": ["the bus comes", "we walk", "we are late"],
        "expected_merges": [],
    },
    {
        "id": "ex-declared-collision",
        "phrases": ["the bus arrives", "the bus arrived", "we walk"],
        "expected_merges": [["the bus arrives", "the bus arrived"]],
    },
]

# Deliberately broken, to prove the check can fail. Keeping a known-bad case next to the good
# ones is the only way to know the guard is doing anything.
UNDECLARED_COLLISION = {
    "id": "ex-undeclared",
    "phrases": ["it is hoping", "it is hopping"],
    "expected_merges": [],
}


def undeclared_collisions(exercise: dict) -> list[tuple[str, str]]:
    """Phrase pairs that share a key but are not declared in `expected_merges`."""
    declared = {frozenset(pair) for pair in exercise["expected_merges"]}
    return [
        (a, b)
        for a, b in combinations(exercise["phrases"], 2)
        if canonical_key(a) == canonical_key(b) and frozenset({a, b}) not in declared
    ]


@pytest.mark.parametrize("exercise", FIXTURES, ids=lambda e: e["id"])
def test_no_bank_exercise_has_an_undeclared_collision(exercise: dict) -> None:
    found = undeclared_collisions(exercise)
    assert not found, f"{exercise['id']} collides on {found} without declaring it"


def test_the_guard_actually_catches_a_collision() -> None:
    assert undeclared_collisions(UNDECLARED_COLLISION) == [("it is hoping", "it is hopping")]


def test_declaring_a_collision_satisfies_the_guard() -> None:
    declared = {**UNDECLARED_COLLISION, "expected_merges": [["it is hoping", "it is hopping"]]}
    assert undeclared_collisions(declared) == []
