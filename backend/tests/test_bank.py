"""The BANK GATE: the three blocking checks that bind when data/exercises.json exists (HLD 17.1.1).

The design says it plainly: *the moment `data/exercises.json` enters the repository, these are
BLOCKING.* They are here, over the real bank, not over fixtures.

  B1 — freshness. `scripts/difficulty.py --check` must agree with the committed `difficulty.json`.
       Also a CI step, because a stale band is inherited silently by band selection, the
       simulation and the results table.
  B2 — the bank guard. No exercise may depend on a student noticing and undoing a false merge.
  B3 — the bank constraint. Every exercise ≤7 relevant clauses, and provable or explicitly marked
       as not following.

Plus the thing that makes the bank worth having: its `expected_entailment` is the AUTHOR'S CLAIM,
and the pipeline is the authority. A disagreement means the exercise is broken.

`backend/tests/test_bank_guard.py` keeps the fixture version of B2, including a deliberately
broken case, because a guard that only ever runs over passing data is a guard nobody has seen fail.
"""

import subprocess
import sys
from itertools import combinations
from pathlib import Path

import pytest
from src.app.data import load_bands, load_bank
from src.core import search, session
from src.core.entail import Verdict
from src.core.facts import canonical_key, polarity

ROOT = Path(__file__).resolve().parents[2]
BANK, META = load_bank()
BANDS = load_bands()
IDS = [exercise.id for exercise in BANK]

# HLD section 2. Not restated from a config constant because it is a BANK authoring rule, not a
# runtime limit: own-question mode may exceed it and degrade via the work budget.
MAX_RELEVANT_CLAUSES = 7


@pytest.fixture(scope="module")
def analysed() -> dict:
    """Every exercise through the real pipeline, once."""
    return {e.id: session.analyse(e.paragraph, e.conclusion) for e in BANK}


# ====================================================================== B3 — the bank constraint


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_parses(exercise_id: str, analysed: dict) -> None:
    refused = [(r.text, r.error_code) for r in analysed[exercise_id].sentences if r.status != "ok"]
    assert not refused, f"{exercise_id}: the bank must not ship a sentence the grammar refuses"


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_matches_its_authors_entailment_claim(
    exercise_id: str, analysed: dict
) -> None:
    # The claim in the file is checked AGAINST the truth table, never trusted instead of it. An
    # exercise whose claim is wrong is a broken exercise -- a student would be coached toward the
    # wrong action all the way through it.
    want = META[exercise_id]["expected_entailment"]
    verdict = analysed[exercise_id].entailment.verdict
    expected = Verdict.ENTAILED if want == "entails" else Verdict.NOT_ENTAILED
    assert verdict is expected, (
        f"{exercise_id}: file claims {want}, truth table says {verdict.name}"
    )


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_is_provable_or_marked_not_following(
    exercise_id: str, analysed: dict
) -> None:
    found = analysed[exercise_id]
    if found.entailment.verdict is not Verdict.ENTAILED:
        assert found.entailment.counterexample is not None, (
            f"{exercise_id}: a does-not-follow exercise must carry a counterexample row to show"
        )
        return
    search.clear_distance_cache()
    steps = search.distance(frozenset([*found.kb, *found.goal]))
    assert steps is not None, f"{exercise_id}: no proof inside the work budget"
    assert 1 <= steps <= 5, f"{exercise_id}: {steps}-step proof is outside the section 9 bands"


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_stays_within_the_relevant_clause_bound(
    exercise_id: str, analysed: dict
) -> None:
    # The bound section 6.6's measured ~57x headroom is stated for. It is only true if the bank
    # honours it, so it is checked here rather than assumed.
    found = analysed[exercise_id]
    if found.relevance is None:
        pytest.skip("inconsistent premises never reach the relevance filter")
    relevant = len(found.relevance.kept) + len(found.goal)
    assert relevant <= MAX_RELEVANT_CLAUSES, f"{exercise_id}: {relevant} relevant clauses"


@pytest.mark.parametrize("exercise_id", IDS)
def test_no_exercise_has_inconsistent_premises(exercise_id: str, analysed: dict) -> None:
    # A contradiction entails everything, so such an exercise halts before Prove and teaches
    # nothing. Legitimate as an own question; never as a shipped exercise.
    verdict = analysed[exercise_id].entailment.verdict
    assert verdict is not Verdict.INCONSISTENT_PREMISES, f"{exercise_id}: premises contradict"


# ========================================================================== B2 — the bank guard


def _identifications(found) -> list[tuple[str, str]]:
    """Phrase pairs the stemmer merges AS THE SAME PROPOSITION -- same key, same polarity.

    Polarity matters, and getting this wrong was the first draft. "the train runs" and "the train
    does not run" share a canonical key, because the key is computed after the embedded negation
    is stripped -- but they are the SAME fact with OPPOSITE signs, which is the designed polarity
    handling and not a merge anyone needs to declare. A polarity-blind check reported five such
    pairs across the bank and would have required the author to declare the obvious; a
    polarity-aware one reports only genuine identifications, which is what v2.7 A7 is about.
    """
    phrases = [text for fact in found.facts for _, text in fact.phrases]
    return [
        (a, b)
        for a, b in combinations(phrases, 2)
        if canonical_key(a) == canonical_key(b) and polarity(a) == polarity(b)
    ]


@pytest.mark.parametrize("exercise_id", IDS)
def test_no_exercise_relies_on_an_undeclared_merge(exercise_id: str, analysed: dict) -> None:
    found = _identifications(analysed[exercise_id])
    declared = {frozenset(pair) for pair in META[exercise_id]["expected_merges"]}
    undeclared = [pair for pair in found if frozenset(pair) not in declared]
    assert not undeclared, (
        f"{exercise_id}: the stemmer merges {undeclared} and the exercise does not declare it. "
        f"A shipped exercise must never depend on a student undoing a false merge (v2.7 A7)."
    )


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_declared_merge_still_actually_happens(exercise_id: str, analysed: dict) -> None:
    # The other direction, and the one that rots. A declared merge the stemmer no longer makes
    # means the exercise now has an extra fact, so its proof and its band both changed -- and the
    # declaration would have gone on claiming otherwise.
    found = {frozenset(pair) for pair in _identifications(analysed[exercise_id])}
    for pair in META[exercise_id]["expected_merges"]:
        assert frozenset(pair) in found, f"{exercise_id}: declared merge {pair} no longer happens"


def test_the_bank_guard_is_not_vacuous() -> None:
    # A check that passes because there is nothing to check is not a check. Exactly one exercise
    # carries a real declared merge (ex-02's tense collapse, HLD section 14.5), so the guard has
    # something to verify in both directions.
    with_merges = [i for i in IDS if META[i]["expected_merges"]]
    assert with_merges, "no exercise declares a merge; B2 would pass vacuously"


@pytest.mark.parametrize("exercise_id", IDS)
def test_a_negation_pair_lands_in_one_fact_with_opposite_signs(
    exercise_id: str, analysed: dict
) -> None:
    # The behaviour the polarity-aware guard above deliberately does NOT ask authors to declare,
    # asserted here instead so it is still covered. "X" and "not X" must be one proposition.
    for fact in analysed[exercise_id].facts:
        texts = [text for _, text in fact.phrases]
        for a, b in combinations(texts, 2):
            assert canonical_key(a) == canonical_key(b), (
                f"{exercise_id}: {fact.symbol} is not one key"
            )
    for fact in analysed[exercise_id].facts:
        keys = {canonical_key(text) for _, text in fact.phrases}
        assert len(keys) == 1, f"{exercise_id}: {fact.symbol} groups two different propositions"


# ============================================================================= B1 — freshness


def test_the_committed_difficulty_data_is_fresh() -> None:
    """BLOCKING. `difficulty.json` must be exactly what the script produces from the bank today.

    Run as a subprocess rather than by calling `compute()`, so this tests the thing CI runs. A
    test that imported the module could pass while the CI invocation was broken.
    """
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "difficulty.py"), "--check"],
        capture_output=True,
        cwd=ROOT,
    )
    assert done.returncode == 0, (
        "data/difficulty.json is stale. Run `python scripts/difficulty.py` and commit.\n"
        + done.stderr.decode("utf-8", "replace")
    )


def test_every_exercise_has_a_band_and_every_band_is_real() -> None:
    assert set(BANDS) == set(IDS), (
        "the derived bands and the bank disagree about which exercises exist"
    )
    assert set(BANDS.values()) <= {"short", "medium", "long"}


def test_the_bands_are_not_all_the_same() -> None:
    # Band selection is the whole point of computing difficulty. A bank that lands in one band
    # makes `next_exercise` pick by ID and the adaptive behaviour untestable.
    assert len(set(BANDS.values())) >= 3, f"only {sorted(set(BANDS.values()))} represented"


def test_difficulty_is_not_stored_in_the_bank() -> None:
    # v2.8 A4a: there must be nowhere for a hand-labelled difficulty to hide.
    import json

    raw = json.loads((ROOT / "data" / "exercises.json").read_text(encoding="utf-8"))
    for row in raw["exercises"]:
        assert not {"difficulty", "band", "proof_length", "steps"} & set(row), (
            f"{row['id']}: difficulty is COMPUTED from the shortest proof, never stored"
        )


# ================================================= the bank's own coverage (sprint addendum 3)


def test_the_bank_covers_every_connective_in_the_grammar() -> None:
    # Section 3.2's productions. A bank that exercises six of nine forms leaves three untested in
    # the only place a student will actually meet them.
    covered = {label for meta in META.values() for label in meta["covers"]}
    for form in (
        "if-then",
        "clause-if-cond",
        "only-if",
        "unless",
        "either-or",
        "neither-nor",
        "iff",
        "both-and",
    ):
        assert form in covered, f"no bank exercise covers {form}"


def test_the_bank_has_enough_long_paragraphs_and_does_not_follow_cases() -> None:
    long_ones = [i for i in IDS if "long paragraph" in META[i]["covers"]]
    not_following = [i for i in IDS if META[i]["expected_entailment"] == "does_not_follow"]
    assert len(long_ones) >= 3, f"only {long_ones} are long paragraphs with distractors"
    assert len(not_following) == 2, (
        f"expected exactly 2 does-not-follow exercises, got {not_following}"
    )


@pytest.mark.parametrize("exercise_id", [i for i in IDS if "long paragraph" in META[i]["covers"]])
def test_every_long_exercise_actually_contains_distractors(
    exercise_id: str, analysed: dict
) -> None:
    # "Long" is not the point; irrelevant premises are. An exercise where everything is needed
    # does not teach the student to notice what is not.
    dropped = analysed[exercise_id].relevance.dropped
    assert len(dropped) >= 2, f"{exercise_id}: only {len(dropped)} clauses are irrelevant"


def test_the_bank_itself_exercises_normalisation() -> None:
    """Sprint addendum 3: the bank must contain punctuation and case variety.

    The fix at S2 -- one preparation function for every entry point -- is only protected if real
    data goes through the messy paths. A bank where every conclusion is a tidy sentence ending in
    a full stop would never have caught the bug that prompted it.
    """
    conclusions = [e.conclusion for e in BANK]
    assert any(c.endswith(".") for c in conclusions), "no conclusion ends in a full stop"
    assert any(c.endswith("!") for c in conclusions), "no conclusion ends in an exclamation mark"
    assert any(c[-1] not in ".!?;" for c in conclusions), "no conclusion omits its terminator"
    assert any(c != c.capitalize() and c[1:] != c[1:].lower() for c in conclusions), (
        "no conclusion uses mixed case"
    )


def test_the_bank_topics_are_distinct() -> None:
    # Twelve exercises on three topics would make the bank feel like three exercises, and would
    # also let one topic's vocabulary quietly carry every test.
    topics = [e.topic for e in BANK]
    assert len(set(topics)) == len(topics), f"repeated topics: {topics}"
    assert len(BANK) == 12, f"the bank is specified as 12 exercises, found {len(BANK)}"
