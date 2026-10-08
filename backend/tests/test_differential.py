"""Differential tests: two independent methods must agree (docs/experiments/differential.md).

The system decides "does this follow" by truth table and "can it be proved" by resolution
search. Those are different algorithms written at different times, and the whole design leans on
them agreeing -- the search is short-circuited whenever the truth table says there is nothing to
find. Testing each against its own expectations would never catch a shared misunderstanding;
testing them against EACH OTHER does.

Counts and seeds are reported in docs/experiments/differential.md.
"""

import random

import pytest
from src.core.entail import Verdict, check, symbols_of
from src.core.logic import is_tautology, resolvents
from src.core.relevance import filter_clauses

SEED = 20261009
EMPTY = frozenset()


def _random_kb(rng: random.Random, symbols: str, max_clauses: int):
    def clause():
        chosen = rng.sample(symbols, rng.randint(1, min(3, len(symbols))))
        return frozenset(("" if rng.random() < 0.5 else "~") + s for s in chosen)

    return [clause() for _ in range(rng.randint(1, max_clauses))]


def _refutation_exists(clauses) -> bool:
    """Saturate under resolution and report whether the empty clause appears.

    Deliberately NOT search.distance(). That answers a different and far harder question -- how
    many steps a student needs -- by exploring clause SETS, and on random knowledge bases it does
    not terminate in reasonable time. Refutation-existence only needs the closure over derivable
    CLAUSES, which is bounded by 3**symbols and finishes instantly.

    Writing it out here also makes the comparison genuinely independent: this shares no code
    path with the truth table beyond the resolution rule itself.
    """
    known = set(clauses)
    if EMPTY in known:
        return True
    frontier = set(known)
    while frontier:
        fresh = set()
        for a in known:
            for b in frontier:
                for resolvent in resolvents(a, b):
                    if resolvent == EMPTY:
                        return True
                    if resolvent not in known and not is_tautology(resolvent):
                        fresh.add(resolvent)
        known |= fresh
        frontier = fresh
    return False


def test_truth_table_and_resolution_agree_on_entailment(record_property) -> None:
    rng = random.Random(SEED)
    entailed = not_entailed = skipped = 0

    for _ in range(600):
        if entailed + not_entailed >= 200:
            break
        kb = _random_kb(rng, "ABCDE", 6)
        goal_symbol = rng.choice("ABCDE")
        negated_goal = [frozenset({("~" if rng.random() < 0.5 else "") + goal_symbol})]

        verdict = check(kb, negated_goal)
        if verdict.verdict is Verdict.INCONSISTENT_PREMISES:
            skipped += 1  # the guarantee only holds for satisfiable premises
            continue

        found = _refutation_exists([*kb, *negated_goal])
        expected = verdict.verdict is Verdict.ENTAILED
        assert found is expected, (
            f"disagreement: truth table says {verdict.verdict.value}, resolution "
            f"{'found' if found else 'did not find'} a refutation.\n"
            f"kb={[sorted(c) for c in kb]} negated_goal={[sorted(c) for c in negated_goal]}"
        )
        entailed += expected
        not_entailed += not expected

    assert entailed + not_entailed == 200
    assert entailed >= 10 and not_entailed >= 10, "one verdict barely occurred -- weak evidence"
    record_property("differential1", f"{entailed} entailed, {not_entailed} not, {skipped} skipped")
    print(f"\nDIFFERENTIAL 1: {entailed} entailed, {not_entailed} not entailed, {skipped} skipped")


def test_relevance_filtering_never_changes_the_verdict(record_property) -> None:
    rng = random.Random(SEED + 1)
    checked = dropped_something = 0

    for _ in range(900):
        if checked >= 200:
            break
        # Two disjoint symbol pools, so a genuine distractor component usually exists.
        kb = _random_kb(rng, "ABC", 4) + _random_kb(rng, "XYZ", 3)
        negated_goal = [frozenset({("~" if rng.random() < 0.5 else "") + rng.choice("ABC")})]

        before = check(kb, negated_goal)
        if before.verdict is Verdict.INCONSISTENT_PREMISES:
            continue

        result = filter_clauses(kb, negated_goal, before)
        assert set(result.kept) <= set(kb), "the filter invented a clause"
        after = check(list(result.kept), negated_goal)
        assert after.verdict is before.verdict, (
            f"filtering changed the verdict {before.verdict.value} -> {after.verdict.value}\n"
            f"kb={[sorted(c) for c in kb]} kept={[sorted(c) for c in result.kept]}"
        )
        checked += 1
        dropped_something += bool(result.dropped)

    assert checked == 200
    assert dropped_something >= 20, "the filter dropped almost nothing -- weak evidence"
    record_property("differential2", f"{checked} checked, {dropped_something} with drops")
    print(f"\nDIFFERENTIAL 2: {checked} checked, {dropped_something} had clauses dropped")


@pytest.mark.parametrize("seed_offset", [0, 1, 2])
def test_agreement_holds_under_other_seeds(seed_offset: int) -> None:
    # A single seed can be lucky. A smaller sweep across three more seeds costs little and
    # would expose a disagreement that only the original seed happened to avoid.
    rng = random.Random(SEED + 100 + seed_offset)
    for _ in range(120):
        kb = _random_kb(rng, "ABCD", 5)
        negated_goal = [frozenset({("~" if rng.random() < 0.5 else "") + rng.choice("ABCD")})]
        verdict = check(kb, negated_goal)
        if verdict.verdict is Verdict.INCONSISTENT_PREMISES:
            continue
        assert _refutation_exists([*kb, *negated_goal]) is (verdict.verdict is Verdict.ENTAILED)


def test_symbols_of_matches_what_the_search_sees() -> None:
    # Both modules must agree on what counts as a symbol, or the truth table would range over a
    # different space than the search explores.
    clauses = [frozenset({"~A", "B"}), frozenset({"C"})]
    assert set(symbols_of(clauses)) == {lit.lstrip("~") for clause in clauses for lit in clause}
