"""Tests for core.tutor -- the orchestrator (docs/HLD.md sections 7, 9, 6.6.1, v2.7 A4).

Written before the implementation.

CONTRACT. `tutor.py` owns four things and no arithmetic:

  1. THE PIPELINE ORDER (section 7). `analyse` runs parse -> facts -> consistency -> entailment ->
     relevance in one place, so the CLI and the API cannot disagree about it.
  2. THE TRANSITION TABLE. The one piece of policy that stays in CODE rather than YAML (v2.10
     item 2), because transitions decide what may happen next and raise named errors.
  3. EVIDENCE. Which skills an action observes, read from `data/policy.yaml` and passed in as
     plain data, with the hint rule applied as a uniform transform. The BKT maths stays in
     `bkt.py`.
  4. SELECTION. Which exercise comes next, and whether the set is finished.

Two properties get the most attention here because both are correctness requirements rather than
conveniences:

  * V-2 (section 6.6): `search` is NEVER called when the conclusion does not follow. The empty
    clause is unreachable there, so BFS would burn the whole work budget on every hint request.
    This is asserted by COUNTING CALLS, not by reading the code.
  * A4 (v2.7): changing a merge re-assigns symbols from scratch, so a proof built on the old
    assignment is no longer about the same propositions. Downstream progress is discarded, and
    the student confirms first.
"""

import copy
import dataclasses
from itertools import product

import pytest
from src.app.data import load_policy
from src.core import search, session, tutor
from src.core.bkt import BktParams, is_done
from src.core.entail import Entailment, Verdict
from src.core.logic import Clause, Code, canonical
from src.core.models import ClauseRec, Fact, MergeChoice, Skill, State, Translation

POLICY = load_policy()
PARAMS = BktParams.from_config()

RAIN = "If it rains then we get wet. It rains."
RAIN_GOAL = "We get wet."

# A 10-sentence paragraph with three sentences the conclusion cannot reach (scenario a).
LONG = (
    "If the server is down then the alert fires. "
    "If the alert fires then the engineer is paged. "
    "If the engineer is paged then the incident opens. "
    "The server is down. "
    "If the canteen is open then the queue is long. "
    "The canteen is open. "
    "If the bus is late then the meeting slips. "
    "The bus is late. "
    "If the incident opens then the report is filed. "
    "If the report is filed then the audit passes."
)
LONG_GOAL = "The audit passes."

# Entailment fails: raining tells us nothing about the bus.
NOT_ENTAILED = "If it rains then we get wet. It rains."
NOT_ENTAILED_GOAL = "The bus is late."


def clauses_of(paragraph: str, conclusion: str) -> frozenset[Clause]:
    found = session.analyse(paragraph, conclusion)
    return frozenset([*found.kb, *found.goal])


@pytest.fixture(autouse=True)
def _fresh_cache():
    # Every case independent: a memoised distance from a previous test would hide a search call
    # the V-2 counters exist to detect.
    search.clear_distance_cache()


def _state(**overrides) -> State:
    base = State(
        mode="practice",
        exercise_id="ex-01",
        stage="prove",
        paragraph=RAIN,
        conclusion=RAIN_GOAL,
        facts=(Fact("A", (("p1", "it rains"),)), Fact("B", (("p2", "we get wet"),))),
        sentences=(),
        merges_applied=(),
        translations=(),
        clauses=(
            ClauseRec("c1", ("A",), "given", "s2"),
            ClauseRec("c2", ("B", "~A"), "given", "s1"),
            ClauseRec("c3", ("~B",), "goal", None),
        ),
        relevant_ids=("c1", "c2", "c3"),
        mastery=dict.fromkeys((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY), 0.3),
        hint_level=0,
        done_ids=(),
        solved=False,
        entailment=Entailment(Verdict.ENTAILED),
    )
    return dataclasses.replace(base, **overrides)


# =============================================================== 1. the pipeline order (section 7)


def test_analyse_runs_the_whole_pipeline_on_the_rain_example() -> None:
    found = session.analyse(RAIN, RAIN_GOAL)
    assert [rec.status for rec in found.sentences] == ["ok", "ok", "ok"]  # conclusion last
    assert {fact.symbol for fact in found.facts} == {"A", "B"}
    assert found.entailment.verdict is Verdict.ENTAILED
    assert sorted(canonical(c) for c in found.kb) == [("A",), ("B", "~A")]
    assert [canonical(c) for c in found.goal] == [("~B",)]
    assert found.relevance is not None and not found.relevance.dropped


def test_the_conclusion_is_the_last_sentence_record() -> None:
    # section 4 says "paragraph sentences in order, conclusion last". POSITION is the only marker
    # -- there is deliberately no `origin` field, because a second source of truth about which
    # record is the conclusion is a second thing that can disagree with the first.
    found = session.analyse(RAIN, RAIN_GOAL)
    assert [rec.text for rec in found.sentences[:-1]] == [
        "If it rains then we get wet",
        "It rains",
    ]
    # The conclusion is normalized by the SAME splitter, so its trailing stop is gone too. The
    # first draft passed it raw, which made "we get wet." and "we get wet" two different facts
    # and quietly stopped the rain example entailing -- a wrong answer, not a crash.
    assert found.sentences[-1].text == "We get wet"


def test_a_long_paragraph_with_distractors_keeps_the_distractors_visible() -> None:
    # Scenario (a). Nothing is DELETED -- relevance reports what the conclusion cannot reach, and
    # the student may still use any clause (section 6.5).
    found = session.analyse(LONG, LONG_GOAL)
    assert all(rec.status == "ok" for rec in found.sentences)
    assert found.entailment.verdict is Verdict.ENTAILED
    assert found.relevance.dropped, "the canteen and bus sentences cannot reach the audit"
    assert len(found.relevance.kept) + len(found.relevance.dropped) == len(found.kb)


def test_one_unparseable_sentence_does_not_stop_the_others() -> None:
    # Scenario (e): errors are per-sentence. A paragraph is a list of attempts, not a transaction.
    found = session.analyse("It rains. Every student passes. We get wet.", RAIN_GOAL)
    statuses = [(rec.status, rec.error_code) for rec in found.sentences]
    assert ("error", "QUANTIFIER_UNSUPPORTED") in statuses
    assert statuses.count(("ok", None)) == 3


def test_a_conclusion_that_fails_to_parse_is_reported_without_an_entailment() -> None:
    # There is nothing to decide against, so inventing a verdict would be a guess.
    found = session.analyse(RAIN, "Every student passes.")
    assert found.sentences[-1].status == "error"
    assert found.entailment is None and found.relevance is None


def test_logic_mode_is_fol_when_any_sentence_needs_it() -> None:
    # HLD S18.7, Phase 8 scope: detected and recorded, but the pipeline above still ran the
    # unchanged propositional path -- QUANTIFIER_UNSUPPORTED above is proof it is not acted on.
    found = session.analyse("It rains. Every student passes. We get wet.", RAIN_GOAL)
    assert found.logic_mode == "fol"


def test_logic_mode_is_fol_even_when_only_the_conclusion_needs_it() -> None:
    found = session.analyse(RAIN, "Every student passes.")
    assert found.logic_mode == "fol"


def test_logic_mode_is_prop_for_an_ordinary_paragraph() -> None:
    found = session.analyse(RAIN, RAIN_GOAL)
    assert found.logic_mode == "prop"


def test_inconsistent_premises_halt_before_relevance() -> None:
    # Scenario (g), and the reason section 7 fixes the order: with a contradiction the refutation
    # can live entirely in the unreachable component, so filtering could delete the only proof.
    found = session.analyse("It rains. It does not rain.", RAIN_GOAL)
    assert found.entailment.verdict is Verdict.INCONSISTENT_PREMISES
    assert found.relevance is None, "relevance must not run on an inconsistent KB"


def test_a_conclusion_fact_no_premise_mentions_is_a_warning_not_an_error() -> None:
    # Scenario (q), v2.7 A6. Usually a typo -- but also exactly what a "does not follow" exercise
    # looks like, so refusing it would make a whole exercise class impossible to author.
    found = session.analyse(NOT_ENTAILED, NOT_ENTAILED_GOAL)
    assert any("CONCLUSION_FACT_UNSEEN" in w for w in found.warnings)
    assert all(rec.status == "ok" for rec in found.sentences)
    assert found.entailment.verdict is Verdict.NOT_ENTAILED
    assert found.entailment.counterexample is not None


def test_merges_are_replayed_and_change_the_symbol_assignment() -> None:
    # Symbols are re-assigned from scratch on every call (v2.6 A1), which is what makes `analyse`
    # a pure function of (paragraph, conclusion, merges) with no hidden history.
    plain = session.analyse("It is hoping. If it is hopping then we win.", "We win.")
    merged = session.analyse(
        "It is hoping. If it is hopping then we win.",
        "We win.",
        merges=(MergeChoice("p1", "p2", "different"),),
    )
    assert len(plain.facts) < len(merged.facts), (
        "the stemmer merged hoping/hopping; the split undid it"
    )


def test_analyse_is_pure() -> None:
    merges = (MergeChoice("p1", "p2", "same"),)
    before = copy.deepcopy(merges)
    session.analyse(RAIN, RAIN_GOAL, merges=merges)
    assert merges == before


# ================================================== 2. the transition table (totality + totality)


def test_every_stage_action_pair_resolves_or_raises_with_a_name() -> None:
    # TOTALITY, as the student asked: the full product of stage x action. There is no third
    # outcome -- no silent pass, no None -- so a frontend that posts the wrong action in the wrong
    # stage gets a named refusal rather than a half-applied state.
    resolved = refused = 0
    for stage, action in product(tutor.STAGES, tutor.ACTIONS):
        if (stage, action) in tutor.TRANSITIONS:
            assert tutor.advance(stage, action) in tutor.STAGES
            resolved += 1
        else:
            with pytest.raises(tutor.TransitionError, match=action):
                tutor.advance(stage, action)
            refused += 1
    assert resolved + refused == len(tutor.STAGES) * len(tutor.ACTIONS)
    assert resolved == len(tutor.TRANSITIONS)
    # Spelled out, because a product nobody has counted by hand cannot catch a missing row.
    assert (len(tutor.STAGES), len(tutor.ACTIONS)) == (5, 8)


def test_every_transition_lands_where_the_design_says() -> None:
    """The DESTINATIONS, written out independently of the table.

    A MUTATION SURVIVOR found this gap. The totality test above asserts only that `advance`
    returns some stage, so changing `("prove", "merge") -> "facts"` into `-> "prove"` passed the
    whole suite: the v2.7 A4 rewind -- the thing that sends a student back to re-confirm facts
    after their symbols were re-assigned -- was never asserted anywhere.

    Spelled out rather than derived from `TRANSITIONS`, because a test that reads the table it is
    checking agrees with it by construction and can only ever catch a crash.
    """
    assert tutor.TRANSITIONS == {
        ("read", "parse"): "facts",
        ("facts", "merge"): "facts",
        ("facts", "confirm_facts"): "translate",
        ("translate", "translate"): "translate",
        ("translate", "confirm"): "prove",
        ("prove", "step"): "prove",
        ("prove", "hint"): "prove",
        ("prove", "claim_not_provable"): "prove",
        # The A4 rewind. A merge re-assigns symbols from scratch, so the proof is no longer about
        # the same propositions and the student must re-confirm the facts.
        ("prove", "merge"): "facts",
        ("explain", "parse"): "read",
    }


def test_a_merge_in_the_prove_stage_rewinds_to_facts() -> None:
    # The same property as one row above, asserted on its own because it is the one transition
    # that LOSES the student's work, and it should fail loudly rather than as part of a dict.
    assert tutor.advance("prove", "merge") == "facts"
    assert tutor.advance("facts", "merge") == "facts"


@pytest.mark.parametrize("action", ["step", "hint", "claim_not_provable", "translate"])
def test_a_proving_action_before_confirming_facts_is_a_named_error(action: str) -> None:
    """The gap this fix closes: a session used to open straight onto the board.

    The Facts screen is section 14's explicit safety net for a connective mis-splitting a fact
    phrase silently -- a student who never saw it would be proving something they never agreed
    was correct. So every proving action is refused in "facts" with a SPECIFIC error, not the
    generic wrong-stage one: `FactsNotConfirmed` is a `TransitionError`, so existing callers that
    catch the base class still work, but a caller that wants to say "confirm the facts first"
    rather than "wrong stage" can catch the subtype.
    """
    with pytest.raises(tutor.FactsNotConfirmed, match=action):
        tutor.advance("facts", action)


def test_confirming_facts_always_leaves_for_translate() -> None:
    # HLD v2.12 change request: every exercise routes through Translate now, M1 or M2 alike --
    # no per-exercise flag, since `Exercise` is exactly four fields and the no-hardcoding rule
    # rules out special-casing some exercises as M2 and others as M1.
    assert tutor.advance("facts", "confirm_facts") == "translate"


def test_confirm_facts_is_distinct_from_confirm() -> None:
    # Two different transitions, deliberately not sharing a name: "confirm" leaves the Translate
    # stage (M2), "confirm_facts" leaves the Facts stage. A shared name would read as one action
    # with two meanings.
    assert ("facts", "confirm") not in tutor.TRANSITIONS
    assert tutor.advance("translate", "confirm") == "prove"


def test_allowed_agrees_with_the_table() -> None:
    for stage in tutor.STAGES:
        expected = {action for (s, action) in tutor.TRANSITIONS if s == stage}
        assert set(tutor.allowed(stage)) == expected
        assert tutor.allowed(stage) == tuple(sorted(expected)), "must be canonically ordered"


def test_an_unknown_stage_or_action_is_refused_rather_than_ignored() -> None:
    with pytest.raises(tutor.TransitionError):
        tutor.advance("nonsense", "step")
    with pytest.raises(tutor.TransitionError):
        tutor.advance("prove", "nonsense")


def test_the_stages_are_the_data_model_stages_plus_the_m2_insert() -> None:
    # section 4: read | facts | prove | explain, with M2 inserting translate before prove.
    assert tutor.STAGES == ("read", "facts", "translate", "prove", "explain")


def test_hint_is_only_valid_in_prove() -> None:
    # section 8 states this as a 400, and it is WHY TRANSLATE evidence is never hint-affected
    # (section 9): there is no hint in the Translate stage, by design and by schema.
    assert tutor.advance("prove", "hint") == "prove"
    for stage in set(tutor.STAGES) - {"prove"}:
        with pytest.raises(tutor.TransitionError):
            tutor.advance(stage, "hint")


def test_translate_is_only_valid_in_the_translate_stage() -> None:
    assert tutor.advance("translate", "translate") == "translate"
    for stage in set(tutor.STAGES) - {"translate"}:
        with pytest.raises(tutor.TransitionError):
            tutor.advance(stage, "translate")


# ============================================================ 3. evidence (section 9 + hint rule)


@pytest.mark.parametrize(
    ("code", "productive", "trigger"),
    [
        (Code.NO_CLASH, None, "step.NO_CLASH"),
        (Code.DOUBLE_CANCEL, None, "step.DOUBLE_CANCEL"),
        (Code.WRONG_RESOLVENT, None, "step.WRONG_RESOLVENT"),
        (Code.TAUTOLOGY, None, "step.TAUTOLOGY"),
        (Code.DUPLICATE, None, "step.DUPLICATE"),
        (Code.VALID, True, "step.VALID.productive"),
        (Code.VALID, False, "step.VALID.unproductive"),
        (Code.VALID, None, "step.VALID.unknown"),
    ],
)
def test_step_trigger_covers_every_code_and_productivity(code, productive, trigger) -> None:
    assert tutor.step_trigger(code, productive) == trigger


def test_step_trigger_output_is_always_a_real_policy_row() -> None:
    # The cross-check that makes a KeyError unreachable: every trigger this function can emit must
    # exist in the loaded table. `logic.Code` is the authority on the left-hand side.
    for code, productive in product(Code, (True, False, None)):
        assert tutor.step_trigger(code, productive) in POLICY


_TRANSLATION_CODES = (
    "CORRECT",
    "CORRECT_CONTRAPOSITIVE",
    "CONVERSE",
    "MISSING_NEGATION",
    "AND_OR_SWAP",
    "NOT_EQUIVALENT",
)


@pytest.mark.parametrize(
    ("code", "trigger"),
    [
        ("CORRECT", "translate.CORRECT"),
        ("CORRECT_CONTRAPOSITIVE", "translate.CORRECT_CONTRAPOSITIVE"),
        ("CONVERSE", "translate.ERROR"),
        ("MISSING_NEGATION", "translate.ERROR"),
        ("AND_OR_SWAP", "translate.ERROR"),
        ("NOT_EQUIVALENT", "translate.ERROR"),
    ],
)
def test_translate_trigger_covers_every_diagnosis_code(code, trigger) -> None:
    # Section 9: only CORRECT and its contrapositive are RIGHT; the other four translation.py
    # diagnoses all collapse to the one ERROR row -- a hinted TRANSLATE is structurally impossible
    # (V-5), so there is no hint split here the way `step_trigger` has one.
    assert tutor.translate_trigger(code) == trigger


def test_translate_trigger_output_is_always_a_real_policy_row() -> None:
    for code in _TRANSLATION_CODES:
        assert tutor.translate_trigger(code) in POLICY


def test_observe_reads_the_row_and_returns_only_the_skills_it_names() -> None:
    # `null` means NO UPDATE. It is not "wrong", and it must not appear in the result at all --
    # a skill present with any value would be a skill the caller then moves.
    observed = tutor.observe("step.NO_CLASH", False, POLICY)
    assert observed == {Skill.CLASH: False}


def test_observe_applies_the_hint_rule_as_a_uniform_transform() -> None:
    clean = tutor.observe("step.VALID.productive", False, POLICY)
    hinted = tutor.observe("step.VALID.productive", True, POLICY)
    assert clean == {Skill.CLASH: True, Skill.RESOLVE: True, Skill.STRATEGY: True}
    assert hinted == {Skill.CLASH: False, Skill.RESOLVE: False, Skill.STRATEGY: False}


def test_a_hint_never_creates_an_observation_that_was_not_there() -> None:
    # The half of the rule that is easy to get wrong. Without it, asking for a hint would score
    # TRANSLATE on a proof step that never involved translating anything.
    for trigger in POLICY:
        clean = tutor.observe(trigger, False, POLICY)
        hinted = tutor.observe(trigger, True, POLICY)
        assert set(hinted) == set(clean), f"{trigger}: the hint rule changed WHICH skills moved"
        assert all(value is False for value in hinted.values())


def test_a_hinted_accepted_claim_scores_strategy_wrong() -> None:
    # Scenario (o) and the row section 9 spells out: escalating the "it doesn't follow" ladder to
    # level 3 and then clicking it is STRATEGY-wrong even though the claim itself is ACCEPTED.
    accepted = "claim_not_provable.CLAIM_ACCEPTED"
    assert tutor.observe(accepted, False, POLICY) == {Skill.STRATEGY: True}
    assert tutor.observe(accepted, True, POLICY) == {Skill.STRATEGY: False}


def test_the_three_non_evidence_triggers_observe_nothing() -> None:
    for trigger in ("parse_failure", "merge", "hint"):
        assert tutor.observe(trigger, False, POLICY) == {}
        assert tutor.observe(trigger, True, POLICY) == {}


def test_apply_evidence_moves_only_the_observed_skills() -> None:
    mastery = {Skill.CLASH: 0.3, Skill.RESOLVE: 0.3, Skill.STRATEGY: 0.3}
    after = tutor.apply_evidence(mastery, "step.NO_CLASH", False, POLICY, PARAMS)
    assert after[Skill.CLASH] == pytest.approx(0.1932, abs=5e-5)  # the section 17.7 wrong figure
    assert after[Skill.RESOLVE] == 0.3 and after[Skill.STRATEGY] == 0.3


def test_apply_evidence_never_invents_a_skill_the_student_does_not_have() -> None:
    # M1 tracks three skills. A TRANSLATE row must not add a fourth to an M1 session, or the
    # mastery display and `is_done` would start requiring a skill the milestone does not teach.
    m1 = {Skill.CLASH: 0.3, Skill.RESOLVE: 0.3, Skill.STRATEGY: 0.3}
    after = tutor.apply_evidence(m1, "translate.CORRECT", False, POLICY, PARAMS)
    assert set(after) == set(m1), "TRANSLATE must not appear in an M1 mastery map"
    assert after == m1


def test_apply_evidence_is_pure() -> None:
    mastery = {Skill.CLASH: 0.3, Skill.RESOLVE: 0.4, Skill.STRATEGY: 0.5}
    before = copy.deepcopy(mastery)
    tutor.apply_evidence(mastery, "step.VALID.productive", False, POLICY, PARAMS)
    assert mastery == before


def test_every_policy_trigger_can_be_applied_without_a_key_error() -> None:
    # TOTALITY over the product the student asked for: trigger x hint x mode. Mode is passed
    # because a reader expects it to matter; the assertion is that it does not.
    mastery = dict.fromkeys((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY, Skill.TRANSLATE), 0.5)
    seen = set()
    for trigger, hinted in product(sorted(POLICY), (False, True)):
        after = tutor.apply_evidence(mastery, trigger, hinted, POLICY, PARAMS)
        assert set(after) == set(mastery)
        assert all(0.0 < value < 1.0 for value in after.values())
        seen.add((trigger, hinted))
    assert len(seen) == len(POLICY) * 2 == 32


def test_an_unknown_trigger_is_a_named_error_not_a_silent_no_op() -> None:
    # A no-op would be worse than a crash: the student's answer would be scored as nothing, and
    # nobody would ever find out.
    with pytest.raises(KeyError):
        tutor.observe("step.INVENTED", False, POLICY)


# ======================================================== 4. hints: V-2, the ladders, the reveal


def _counting(monkeypatch) -> dict[str, int]:
    calls = {"distance": 0, "best": 0, "fallback": 0}
    for name, key in (
        ("distance", "distance"),
        ("best_next_step", "best"),
        ("fallback_step", "fallback"),
    ):
        original = getattr(search, name)

        def wrapper(*args, _original=original, _key=key, **kwargs):
            calls[_key] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(search, name, wrapper)
    return calls


@pytest.mark.parametrize("level", [1, 2, 3])
def test_v2_no_search_call_at_all_when_the_conclusion_does_not_follow(monkeypatch, level) -> None:
    """BLOCKER V-2 (section 6.6), asserted by COUNTING rather than by reading the code.

    The empty clause is unreachable from a non-entailing clause set, so BFS would exhaust the
    space to the whole work budget on every single hint request. Entailment is already decided by
    truth table before the Prove stage, so the system simply knows.
    """
    calls = _counting(monkeypatch)
    hint = tutor.plan_hint(clauses_of(NOT_ENTAILED, NOT_ENTAILED_GOAL), Verdict.NOT_ENTAILED, level)
    assert calls == {"distance": 0, "best": 0, "fallback": 0}, f"V-2 violated: {calls}"
    assert hint.code == f"HINT_NOT_FOLLOW_{level}"


def test_the_non_entailed_ladder_reveals_nothing_until_level_three() -> None:
    # Levels 1 and 2 describe the METHOD, not the verdict (section 6.6.1), so a student who
    # follows L2 reaches the conclusion themselves. L3 gives it away, deliberately and
    # symmetrically with proof-mode L3, and the BKT penalty is the price.
    state = clauses_of(NOT_ENTAILED, NOT_ENTAILED_GOAL)
    first, second, third = (tutor.plan_hint(state, Verdict.NOT_ENTAILED, n) for n in (1, 2, 3))
    assert first.reveals_the_answer is False
    assert second.reveals_the_answer is False
    assert third.reveals_the_answer is True


def test_an_inconsistent_kb_also_never_searches(monkeypatch) -> None:
    # The other non-entailing verdict. An inconsistent KB refutes itself, so a hint about the
    # student's goal would be meaningless -- and the exercise halts before Prove anyway.
    calls = _counting(monkeypatch)
    hint = tutor.plan_hint(frozenset(), Verdict.INCONSISTENT_PREMISES, 1)
    assert calls == {"distance": 0, "best": 0, "fallback": 0}
    assert hint.code == "HINT_NOT_FOLLOW_1"


@pytest.mark.parametrize("level", [1, 2, 3])
def test_the_proof_ladder_reveals_exactly_as_much_as_the_level_earns(level) -> None:
    # The REVEAL is enforced by what the Hint object CARRIES, not by what the frontend chooses to
    # render. A payload that held the resolvent at level 1 would leak the answer to anyone with
    # the developer console open, however careful the UI was.
    hint = tutor.plan_hint(clauses_of(RAIN, RAIN_GOAL), Verdict.ENTAILED, level)
    assert hint.code == f"HINT_{level}"
    assert len(hint.clauses) == min(level, 2)
    assert (hint.resolvent is not None) == (level == 3)
    assert hint.reveals_the_answer == (level == 3)


def test_the_revealed_clauses_are_a_prefix_of_the_next_level() -> None:
    # An escalating ladder: level 2 must name the SAME first clause as level 1 and add the second.
    # Two unrelated suggestions would make the ladder feel random and would waste a level.
    state = clauses_of(RAIN, RAIN_GOAL)
    first, second, third = (tutor.plan_hint(state, Verdict.ENTAILED, n) for n in (1, 2, 3))
    assert second.clauses[:1] == first.clauses
    assert third.clauses == second.clauses


def test_the_level_three_resolvent_is_actually_the_first_step_of_a_shortest_proof() -> None:
    state = clauses_of(RAIN, RAIN_GOAL)
    hint = tutor.plan_hint(state, Verdict.ENTAILED, 3)
    assert search.productive(state, state | {hint.resolvent}) is True


def test_a_solved_board_has_no_hint_to_give() -> None:
    solved = clauses_of(RAIN, RAIN_GOAL) | {search.EMPTY_CLAUSE}
    assert tutor.plan_hint(solved, Verdict.ENTAILED, 1).code == "HINT_UNAVAILABLE"


def test_an_entailed_verdict_on_a_board_with_no_refutation_raises_rather_than_guessing() -> None:
    """V-2's precondition is load-bearing, and this is the test that proves it.

    `{A}, {B}` has no refutation. An ENTAILED verdict for it is a CALLER bug -- the truth table
    settled the question before the Prove stage -- and the honest response is the named error
    `search` already raises, not a `HINT_UNAVAILABLE` that would make the board look exhausted.

    It also means there is no reachable "entailed but no legal step" case: an entailed, unsolved
    clause set has a refutation, so it has at least one legal step. A HINT_UNAVAILABLE branch
    there would be dead code (CLAUDE.md rule 3).
    """
    with pytest.raises(search.GoalUnreachableError):
        tutor.plan_hint(frozenset({frozenset({"A"}), frozenset({"B"})}), Verdict.ENTAILED, 2)


def test_the_budget_falls_back_to_a_rule_instead_of_hanging(monkeypatch) -> None:
    # Scenario (l). A one-unit budget guarantees the search runs out, which is the documented
    # behaviour for an own question whose proof is deeper than the budget reaches.
    monkeypatch.setattr(tutor.config, "MAX_SEARCH_WORK", 1)
    hint = tutor.plan_hint(clauses_of(RAIN, RAIN_GOAL), Verdict.ENTAILED, 3)
    assert hint.code == "HINT_FALLBACK"
    assert hint.resolvent is not None, "a fallback still suggests a legal step"
    assert hint.reveals_the_answer is True


def test_the_fallback_prefers_the_shortest_clause(monkeypatch) -> None:
    # The documented rule (section 6.6): unit clauses are what actually drive a refutation to the
    # empty clause, so the heuristic is cheap and usually sensible -- and labelled a suggestion.
    monkeypatch.setattr(tutor.config, "MAX_SEARCH_WORK", 1)
    hint = tutor.plan_hint(clauses_of(LONG, LONG_GOAL), Verdict.ENTAILED, 2)
    assert hint.code == "HINT_FALLBACK"
    assert min(len(c) for c in hint.clauses) == 1


@pytest.mark.parametrize("level", [0, 4, -1])
def test_a_level_outside_the_ladder_is_refused(level) -> None:
    with pytest.raises(ValueError, match="level"):
        tutor.plan_hint(clauses_of(RAIN, RAIN_GOAL), Verdict.ENTAILED, level)


def test_plan_hint_is_pure() -> None:
    state = clauses_of(RAIN, RAIN_GOAL)
    before = copy.deepcopy(state)
    tutor.plan_hint(state, Verdict.ENTAILED, 3)
    assert state == before


# ======================================================= 5. hint-level tracking and its resets


def test_asking_for_a_hint_raises_the_level_and_never_lowers_it() -> None:
    state = _state(hint_level=0)
    for expected in (1, 2, 3, 3):
        state = session.record_hint(state)
        assert state.hint_level == expected
    assert state.hint_level == 3, "the ladder tops out rather than wrapping"


def test_adding_a_clause_resets_the_hint_level() -> None:
    # section 4: "0-3; resets on stage change or a clause being added". The board has changed, so
    # the old hint was about a position that no longer exists -- and charging the student's next
    # step as hinted would punish them for help they did not get.
    state = session.record_hint(session.record_hint(_state()))
    assert state.hint_level == 2
    advanced = session.record_clause(state, ClauseRec("c4", ("B",), "derived", None))
    assert advanced.hint_level == 0
    assert advanced.clauses[-1].id == "c4"


def test_a_derived_clause_is_added_to_relevant_ids() -> None:
    # section 6.5's filter only ever ran over the ORIGINAL premises, so a clause the student just
    # derived was never in it -- and "not needed for this conclusion" is a claim about premises,
    # not about something built while working toward the goal. Leaving it out mislabels it.
    state = _state(relevant_ids=("c1", "c2", "c3"))
    advanced = session.record_clause(state, ClauseRec("c4", ("B",), "derived", None))
    assert advanced.relevant_ids == ("c1", "c2", "c3", "c4")


def test_changing_stage_resets_the_hint_level() -> None:
    state = session.record_hint(_state(stage="prove"))
    assert session.enter_stage(state, "explain").hint_level == 0


def test_staying_in_the_same_stage_does_not_reset_the_hint_level() -> None:
    # Otherwise every step inside Prove would clear the ladder and a hint would never cost
    # anything, which would quietly disable the whole BKT hint rule.
    state = session.record_hint(_state(stage="prove"))
    assert session.enter_stage(state, "prove").hint_level == 1


def test_deriving_the_empty_clause_solves_the_exercise_and_moves_to_explain() -> None:
    state = session.record_clause(_state(), ClauseRec("c4", (), "derived", None))
    assert state.solved is True
    assert state.stage == "explain"
    assert state.hint_level == 0


def test_record_translation_stores_the_attempt() -> None:
    state = session.record_translation(_state(), "s1", "A -> B", "CORRECT")
    assert state.translations == (Translation("s1", "A -> B", "done", "CORRECT"),)


def test_record_translation_replaces_an_earlier_attempt_at_the_same_sentence() -> None:
    # A retry is a correction, not a second data point -- section 9 scores the attempt the
    # student leaves on screen, so an earlier wrong guess at the same sentence must not survive.
    state = session.record_translation(_state(), "s1", "A -> B", "CONVERSE")
    retried = session.record_translation(state, "s1", "B -> A", "CORRECT")
    assert retried.translations == (Translation("s1", "B -> A", "done", "CORRECT"),)


# ========================================================== 6. the downstream reset (v2.7 A4)


def test_changing_a_merge_mid_proof_requires_confirmation_first() -> None:
    # The student must confirm BEFORE the change applies, because they are about to lose work
    # they cannot see is at risk.
    state = _state(stage="prove")
    with pytest.raises(session.ResetRequired, match="confirm"):
        session.change_merges(state, (MergeChoice("p1", "p2", "same"),), confirmed=False)


def test_a_confirmed_merge_change_discards_exactly_the_downstream_work() -> None:
    # A4: symbols are re-assigned from scratch on every merge, so a proof built on the old
    # assignment is no longer ABOUT the same propositions. Keeping it would be worse than losing
    # it -- the board would silently mean something else.
    state = _state(
        stage="prove",
        hint_level=3,
        solved=True,
        translations=(Translation("s1", "R -> C", "correct"),),
        clauses=(
            ClauseRec("c1", ("A",), "given", "s2"),
            ClauseRec("c2", ("B", "~A"), "given", "s1"),
            ClauseRec("c3", ("~B",), "goal", None),
            ClauseRec("c4", ("B",), "derived", None),
        ),
    )
    after = session.change_merges(state, (MergeChoice("p1", "p2", "same"),), confirmed=True)

    assert after.stage == "facts", "the student is sent back to re-confirm the facts"
    assert after.translations == ()
    assert after.clauses == (), "clauses are re-derived from the new symbols, not carried over"
    assert after.relevant_ids == ()
    assert after.hint_level == 0 and after.solved is False
    assert after.merges_applied == (MergeChoice("p1", "p2", "same"),)


def test_a_merge_change_keeps_what_is_not_downstream() -> None:
    # Mastery is about the STUDENT, not about this board, so it survives. So does the exercise
    # and the set of exercises already done -- losing those would punish a correction.
    state = _state(stage="prove", mastery={Skill.CLASH: 0.8}, done_ids=("ex-00",))
    after = session.change_merges(state, (), confirmed=True)
    assert after.mastery == {Skill.CLASH: 0.8}
    assert after.done_ids == ("ex-00",)
    assert after.exercise_id == "ex-01"
    assert (after.paragraph, after.conclusion) == (state.paragraph, state.conclusion)


def test_the_merge_change_is_pure() -> None:
    state = _state(stage="prove", hint_level=2)
    before = copy.deepcopy(state)
    session.change_merges(state, (MergeChoice("p1", "p2", "same"),), confirmed=True)
    assert state == before


def test_a_merge_change_is_not_evidence() -> None:
    # The user is the authority on what their own words mean, so there is no ground truth to
    # score against (section 9). A merge that moved mastery would punish honesty.
    assert tutor.observe("merge", False, POLICY) == {}


# ============================================================ 7. next_exercise (section 9 bands)

BANK = ("ex-01", "ex-02", "ex-03", "ex-04", "ex-05", "ex-06")
BANDS = {
    "ex-01": "short",
    "ex-02": "short",
    "ex-03": "medium",
    "ex-04": "medium",
    "ex-05": "long",
    "ex-06": "long",
}


def _bank():
    from src.core.models import Exercise

    return tuple(Exercise(i, "p", "c", "topic") for i in BANK)


@pytest.mark.parametrize(
    ("mean", "band"),
    [
        (0.0, "short"),
        (0.39, "short"),
        (0.4, "medium"),
        (0.8, "medium"),
        (0.81, "long"),
        (1.0, "long"),
    ],
)
def test_the_band_comes_from_the_mean_mastery(mean, band) -> None:
    # section 9: <0.4 short, 0.4-0.8 medium, >0.8 long. The boundaries are asserted because an
    # off-by-one in a closed interval sends every mid-range student to the wrong band.
    assert tutor.band_of_mastery(dict.fromkeys((Skill.CLASH, Skill.RESOLVE), mean)) == band


def test_next_exercise_is_total_over_the_mastery_grid() -> None:
    # The student's grid: every skill in {0, 0.2, ..., 1.0}. Either the set is finished or there
    # is an exercise -- there is no third answer, and no combination may fall through.
    grid = [round(0.2 * n, 1) for n in range(6)]
    answered = 0
    for values in product(grid, repeat=3):
        mastery = dict(zip((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY), values, strict=True))
        chosen = tutor.next_exercise(_bank(), BANDS, mastery, ())
        assert chosen is not None and chosen.id in BANK
        answered += 1
    assert answered == len(grid) ** 3 == 216


def test_next_exercise_is_deterministic() -> None:
    mastery = dict.fromkeys((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY), 0.5)
    once = tutor.next_exercise(_bank(), BANDS, mastery, ())
    assert all(tutor.next_exercise(_bank(), BANDS, mastery, ()) == once for _ in range(5))


def test_unseen_exercises_come_first_sorted_by_id() -> None:
    low = dict.fromkeys((Skill.CLASH,), 0.1)  # short band
    assert tutor.next_exercise(_bank(), BANDS, low, ()).id == "ex-01"
    assert tutor.next_exercise(_bank(), BANDS, low, ("ex-01",)).id == "ex-02"


def test_an_empty_band_falls_to_the_nearest_one_with_ties_toward_the_easier() -> None:
    # A student in the medium band with both medium exercises done should be offered the SHORT
    # one, not the long one: being handed something harder than the band after exhausting it is
    # how a formative system turns into a wall.
    medium = dict.fromkeys((Skill.CLASH,), 0.5)
    chosen = tutor.next_exercise(_bank(), BANDS, medium, ("ex-03", "ex-04"))
    assert chosen.id in ("ex-01", "ex-02") and chosen.id == "ex-01"


def test_a_long_band_student_with_no_long_exercises_left_gets_medium() -> None:
    high = dict.fromkeys((Skill.CLASH,), 0.95)
    chosen = tutor.next_exercise(_bank(), BANDS, high, ("ex-05", "ex-06"))
    assert BANDS[chosen.id] == "medium", "the nearest band, not the easiest"


def test_an_exhausted_bank_repeats_the_least_recently_seen() -> None:
    # Repeats are the documented behaviour, not an error: a student who has seen everything and
    # has not mastered it needs another attempt, and the oldest one is the least fresh in memory.
    mastery = dict.fromkeys((Skill.CLASH,), 0.5)
    seen = ("ex-03", "ex-01", "ex-05", "ex-02", "ex-06", "ex-04")
    assert tutor.next_exercise(_bank(), BANDS, mastery, seen).id == "ex-03"


def test_a_repeat_breaks_ties_by_lowest_id() -> None:
    # Two exercises last seen at the same point cannot happen in a real log, but the rule is
    # written down (section 9) and a tie-break that is not asserted is a tie-break that drifts.
    mastery = dict.fromkeys((Skill.CLASH,), 0.5)
    assert tutor.next_exercise(_bank(), BANDS, mastery, BANK).id == "ex-01"


def test_a_repeated_id_counts_from_its_most_recent_sighting() -> None:
    # done_ids is a log, so an id can appear twice. "Least recently seen" means the LAST sighting;
    # using the first would keep re-offering whatever the student has just done.
    mastery = dict.fromkeys((Skill.CLASH,), 0.5)
    seen = (*BANK, "ex-01")  # ex-01 was oldest, then became the newest
    assert tutor.next_exercise(_bank(), BANDS, mastery, seen).id == "ex-02"


def test_an_empty_bank_has_no_next_exercise() -> None:
    assert tutor.next_exercise((), {}, {Skill.CLASH: 0.5}, ()) is None


def test_an_exercise_with_no_band_is_still_offered_and_never_crashes() -> None:
    # The bank guard and the freshness check should make this impossible, but a missing band must
    # degrade to "offer it anyway" rather than hiding an exercise from every student forever.
    from src.core.models import Exercise

    bank = (*_bank(), Exercise("ex-99", "p", "c", "t"))
    chosen = tutor.next_exercise(bank, BANDS, dict.fromkeys((Skill.CLASH,), 0.5), BANK)
    assert chosen.id == "ex-99", "an unbanded unseen exercise still beats a repeat"


def test_next_exercise_is_pure() -> None:
    mastery = dict.fromkeys((Skill.CLASH,), 0.5)
    bands, done = dict(BANDS), ("ex-01",)
    before = (copy.deepcopy(mastery), copy.deepcopy(bands), copy.deepcopy(done))
    tutor.next_exercise(_bank(), bands, mastery, done)
    assert (mastery, bands, done) == before


def test_the_done_check_lives_with_the_maths_it_is_made_of() -> None:
    # `is_done` is a threshold test on the posterior, so it belongs beside the update that
    # produces it, not in the policy module. There is deliberately NO re-export: a second name
    # for one function is a second thing to keep in step (v2.11 moved the section 4.1 row).
    at = PARAMS.threshold
    assert is_done(dict.fromkeys((Skill.CLASH, Skill.RESOLVE), at), PARAMS)
    assert not is_done({}, PARAMS)
    assert not hasattr(tutor, "is_done")


# ======================================================== 8. end-to-end, pure core, no API at all


def test_end_to_end_the_rain_example_from_paragraph_to_solved() -> None:
    """The whole M1 flow through core alone: parse, facts, entail, relevance, prove, solved.

    No API, no CLI, no file. If this test needs a server to run, core has stopped being pure.
    """
    found = session.analyse(RAIN, RAIN_GOAL)
    assert found.entailment.verdict is Verdict.ENTAILED

    board = frozenset([*found.kb, *found.goal])
    mastery = dict.fromkeys((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY), 0.3)
    steps = 0
    while search.EMPTY_CLAUSE not in board:
        hint = tutor.plan_hint(board, Verdict.ENTAILED, 3)
        assert hint.code == "HINT_3"
        verdict = search.productive(board, board | {hint.resolvent})
        mastery = tutor.apply_evidence(
            mastery, tutor.step_trigger(Code.VALID, verdict), False, POLICY, PARAMS
        )
        board |= {hint.resolvent}
        steps += 1
        assert steps <= 5, "the rain example is a two-step proof; this is not converging"

    assert steps == 2, "~A v B, A, ~B refutes in two resolutions"
    assert all(value > 0.3 for value in mastery.values()), "a clean proof raises every skill"


def test_end_to_end_a_long_paragraph_with_distractors_still_proves() -> None:
    found = session.analyse(LONG, LONG_GOAL)
    board = frozenset([*found.kb, *found.goal])
    assert found.relevance.dropped, "the distractors must be reported"

    for _ in range(12):
        if search.EMPTY_CLAUSE in board:
            break
        hint = tutor.plan_hint(board, Verdict.ENTAILED, 3)
        assert hint.code == "HINT_3", f"the budget should reach this depth: {hint.code}"
        board |= {hint.resolvent}
    assert search.EMPTY_CLAUSE in board


def test_end_to_end_a_not_entailed_exercise_with_a_correct_claim(monkeypatch) -> None:
    # Scenario (h). The whole point of V-2: the student is coached toward the right ACTION, and
    # no search runs at any point in the exercise.
    calls = _counting(monkeypatch)
    found = session.analyse(NOT_ENTAILED, NOT_ENTAILED_GOAL)
    assert found.entailment.verdict is Verdict.NOT_ENTAILED
    assert found.entailment.counterexample is not None

    board = frozenset([*found.kb, *found.goal])
    assert tutor.plan_hint(board, found.entailment.verdict, 2).code == "HINT_NOT_FOLLOW_2"

    mastery = dict.fromkeys((Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY), 0.5)
    accepted = tutor.apply_evidence(
        mastery, "claim_not_provable.CLAIM_ACCEPTED", False, POLICY, PARAMS
    )
    assert accepted[Skill.STRATEGY] > 0.5
    # ...but a hinted claim is scored wrong even though it is accepted (section 9).
    hinted = tutor.apply_evidence(
        mastery, "claim_not_provable.CLAIM_ACCEPTED", True, POLICY, PARAMS
    )
    assert hinted[Skill.STRATEGY] < 0.5
    assert calls == {"distance": 0, "best": 0, "fallback": 0}


def test_end_to_end_a_wrong_not_provable_claim_on_a_provable_exercise() -> None:
    # Scenario (i). The claim is REJECTED and STRATEGY is scored wrong -- the student gave up on
    # something that does follow.
    found = session.analyse(RAIN, RAIN_GOAL)
    assert found.entailment.verdict is Verdict.ENTAILED
    mastery = dict.fromkeys((Skill.STRATEGY,), 0.5)
    after = tutor.apply_evidence(
        mastery, "claim_not_provable.CLAIM_REJECTED", False, POLICY, PARAMS
    )
    assert after[Skill.STRATEGY] < 0.5


def test_tutor_reads_no_file() -> None:
    # Core never touches the filesystem: the policy table arrives as plain data from the edge.
    import ast

    tree = ast.parse(open(tutor.__file__, encoding="utf-8").read())
    imported = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"json", "yaml", "pathlib", "io", "os"}, f"tutor.py imports {imported}"
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in called
