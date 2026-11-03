"""Tests for app.render's FOL proof-trace rendering (HLD section 18.14).

Written before the implementation. `fol_proof_trace()` turns a `FolSearchResult`'s
already-computed `proof_steps` into labeled clauses + an ordered step list for the Explanation
tab's read-only view -- it adds no new logic, only labels and renders what `fol_prove()` already
decided. Takes `FolSearchResult`, not the `FolSessionResult` that lives on `State`: a `Predicate`
contains a recursive `Term` union, and putting one on `State` crashes
`test_every_state_field_is_json_representable` with `RecursionError` (confirmed directly) rather
than failing cleanly -- so the raw trace is recomputed at the API edge per request, never
persisted, same ephemeral treatment `fol_message` already gets.

Some cases are built directly as `FolSearchResult`/`FolClause` values rather than through
`fol_prove()`, for the same reason `test_fol_search.py` hand-builds `FolFormula` trees: a clause
containing a Skolem `FunctionTerm`, or a clause deliberately reused across two steps, is easier to
construct by hand than to coax out of the real CNF pipeline, and the renderer must not care which
produced its input.
"""

from src.app.render import Renderer
from src.core.fol_models import (
    Constant,
    FolImplies,
    FolNot,
    ForAll,
    FunctionTerm,
    Predicate,
    Variable,
)
from src.core.fol_search import EMPTY_CLAUSE, FolProofOutcome, FolSearchResult, fol_prove
from src.core.fol_step import FolStepError, parse_clause_text

x = Variable("x")
socrates = Constant("socrates")

RENDERER = Renderer(text={})  # fol_proof_trace uses no yaml templates -- pure structural rendering


def human(t: object) -> Predicate:
    return Predicate("Human", (t,))  # type: ignore[arg-type]


def mortal(t: object) -> Predicate:
    return Predicate("Mortal", (t,))  # type: ignore[arg-type]


# ------------------------------------------------------------------------------------- PROVED


def test_proved_trace_labels_premises_first_then_derived_clauses_in_order() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)

    assert len(trace.steps) == len(found.proof_steps)
    # The final step's resolvent is the empty clause, and its label's own text is "□" --
    # the proof's conclusion is visible from the legend alone, no special-casing needed.
    last_resolvent_label = trace.steps[-1].resolvent
    assert trace.clauses[last_resolvent_label] == "□ (empty clause)"


def test_proved_trace_renders_readable_clause_text() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)

    rendered = set(trace.clauses.values())
    assert "Human(socrates)" in rendered
    assert any("¬Human" in text and "Mortal" in text for text in rendered)


def test_proved_trace_has_no_unrendered_terms_without_skolemization() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    assert RENDERER.fol_proof_trace(found).has_unrendered_terms is False


# ------------------------------------------------------------------------------- BUDGET_EXHAUSTED


def test_budget_exhausted_trace_never_ends_in_the_empty_clause() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, Predicate("Zebra", (socrates,)), budget=3)  # type: ignore[arg-type]
    assert found.outcome is FolProofOutcome.BUDGET_EXHAUSTED
    trace = RENDERER.fol_proof_trace(found)
    # Partial work may be shown, but it must never render as a completed proof -- no step's
    # resolvent may be the empty clause, since the search never found one.
    assert all(trace.clauses[step.resolvent] != "□ (empty clause)" for step in trace.steps)


# --------------------------------------------------------------------- zero-step INCONSISTENT


def test_empty_proof_steps_yields_an_empty_trace() -> None:
    # Unreachable from the bounded grammar in practice (every pattern yields a non-empty
    # Predicate), but a zero-step result must still render something sane rather than crash --
    # the already-shown fol_message explains the "why".
    found = FolSearchResult(FolProofOutcome.INCONSISTENT, [], frozenset({EMPTY_CLAUSE}))
    trace = RENDERER.fol_proof_trace(found)
    assert trace == RENDERER.fol_proof_trace(found)  # same shape, deterministic
    assert trace.clauses == {}
    assert trace.steps == ()
    assert trace.has_unrendered_terms is False


# --------------------------------------------------------------------------- Skolem-term fallback


def test_a_skolem_function_term_renders_without_crashing_and_sets_the_flag() -> None:
    sk0 = FunctionTerm("sk_f0", (x,))  # type: ignore[arg-type]
    loves_x_sk0 = frozenset({(True, Predicate("Loves", (x, sk0)))})
    not_loves = frozenset({(False, Predicate("Loves", (x, sk0)))})
    step = (loves_x_sk0, not_loves, EMPTY_CLAUSE, {})
    found = FolSearchResult(FolProofOutcome.PROVED, [step], frozenset({loves_x_sk0, not_loves}))
    trace = RENDERER.fol_proof_trace(found)

    assert trace.has_unrendered_terms is True
    rendered = " ".join(trace.clauses.values())
    assert "f1(x)" in rendered  # exam notation; never crashes, never silently dropped
    assert "sk_f0" not in rendered  # the internal counter name never reaches the student


def test_a_clause_with_no_function_terms_does_not_set_the_flag() -> None:
    clause_a = frozenset({(True, human(socrates))})
    clause_b = frozenset({(False, human(socrates))})
    step = (clause_a, clause_b, EMPTY_CLAUSE, {})
    found = FolSearchResult(FolProofOutcome.PROVED, [step], frozenset({clause_a, clause_b}))
    assert RENDERER.fol_proof_trace(found).has_unrendered_terms is False


# --------------------------------------------------------------------------------- labeling rules


def test_a_clause_reused_across_two_steps_keeps_its_first_label() -> None:
    # Human(socrates) resolves against two different clauses in two separate steps -- it must
    # keep ONE label throughout, not be relabeled the second time it appears.
    human_socrates = frozenset({(True, human(socrates))})
    not_human_or_mortal = frozenset({(False, human(socrates)), (True, mortal(socrates))})
    not_human_or_zebra = frozenset(
        {(False, human(socrates)), (True, Predicate("Zebra", (socrates,)))}  # type: ignore[arg-type]
    )
    step1 = (human_socrates, not_human_or_mortal, frozenset({(True, mortal(socrates))}), {})
    step2 = (
        human_socrates,
        not_human_or_zebra,
        frozenset({(True, Predicate("Zebra", (socrates,)))}),
        {},
    )
    found = FolSearchResult(FolProofOutcome.BUDGET_EXHAUSTED, [step1, step2], frozenset())
    trace = RENDERER.fol_proof_trace(found)

    assert trace.steps[0].left == trace.steps[1].left  # same clause, same label both times
    assert len({trace.steps[0].left, trace.steps[0].right, trace.steps[1].right}) == 3


def test_labels_assigned_in_first_appearance_order_not_sorted() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    assert list(trace.clauses) == [f"F{n}" for n in range(1, len(trace.clauses) + 1)]


# -------------------------------------------------- variable names are clause-local, not pipeline
# -------------------------------------------------- internals (found live, 2026-11-02)


def test_a_pipeline_internal_variable_name_never_reaches_the_student() -> None:
    # standardize_apart_clauses (HLD S18.3 step 8) renames variables to something like
    # "c0_v0" so two different clauses' same-looking x never collide during resolution --
    # that disambiguation is internal; a student reading the trace must see "x", never "c0_v0".
    weird_name_clause = frozenset({(True, Predicate("Human", (Variable("c0_v0"),)))})  # type: ignore[arg-type]
    other = frozenset({(False, Predicate("Human", (Variable("c0_v0"),)))})  # type: ignore[arg-type]
    step = (weird_name_clause, other, EMPTY_CLAUSE, {})
    found = FolSearchResult(FolProofOutcome.PROVED, [step], frozenset({weird_name_clause, other}))
    trace = RENDERER.fol_proof_trace(found)
    rendered = " ".join(trace.clauses.values())
    assert "c0_v0" not in rendered
    assert "Human(x)" in rendered


def test_two_different_clauses_get_independent_variable_names() -> None:
    # Clause-local renaming must not accidentally make two DIFFERENT variables look the same
    # across clauses in a way that implies a relationship that is not there -- each clause's "x"
    # is independent, matching the underlying standardize-apart invariant it is standing in for.
    c1 = frozenset({(True, Predicate("P", (Variable("c0_v0"),)))})  # type: ignore[arg-type]
    c2 = frozenset({(True, Predicate("Q", (Variable("c1_v0"),)))})  # type: ignore[arg-type]
    step = (c1, c2, EMPTY_CLAUSE, {})
    found = FolSearchResult(FolProofOutcome.PROVED, [step], frozenset({c1, c2}))
    trace = RENDERER.fol_proof_trace(found)
    assert trace.clauses["F1"] == "P(x)"
    assert trace.clauses["F2"] == "Q(x)"  # independently named "x" too -- clause-local, not shared


# --------------------------- exam-form trace: full clause legend (item 1, 2026-11-02)

# The step table cites F1..Fn but a reader cannot check a proof whose clauses are never shown,
# and an examiner needs EVERY input clause listed, including any the derivation never used.


def test_legend_defines_every_label_the_steps_cite() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    defined = {entry.label for entry in trace.legend}
    cited = {label for step in trace.steps for label in (step.left, step.right, step.resolvent)}
    assert cited <= defined
    assert all(entry.text for entry in trace.legend)


def test_legend_lists_input_clauses_even_when_the_derivation_never_uses_them() -> None:
    # "Zebra(socrates)" is irrelevant to the Socrates proof, so no resolution step touches it --
    # it must still appear in the clause list an examiner reads.
    irrelevant = Predicate("Zebra", (socrates,))
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates), irrelevant]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    assert any("Zebra" in entry.text for entry in trace.legend)


def test_legend_marks_each_clause_origin() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    origins = {entry.origin for entry in trace.legend}
    assert origins == {"premise", "negated_goal", "derived"}


def test_legend_lists_inputs_before_derived_clauses() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    origins = [entry.origin for entry in trace.legend]
    assert origins.index("derived") > max(
        index for index, origin in enumerate(origins) if origin != "derived"
    )


def test_legend_labels_are_unique_and_match_the_clauses_dict() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    labels = [entry.label for entry in trace.legend]
    assert len(labels) == len(set(labels))
    for entry in trace.legend:
        assert trace.clauses[entry.label] == entry.text


# ------------- negated-goal caption + exam-form conclusion (items 2 and 3, 2026-11-02)

CAPTIONED = Renderer(
    text={
        "fol": {
            "negated_goal": "Negated for refutation.",
            "conclusion_proved": "{premises} together with {negated} is unsatisfiable, "
            "so {goal} is proved.",
        }
    }
)


def test_the_negated_goal_clause_carries_its_caption() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    goal_entries = [entry for entry in trace.legend if entry.origin == "negated_goal"]
    assert len(goal_entries) == 1
    assert goal_entries[0].note == "Negated for refutation."


def test_premise_clauses_carry_no_caption() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    assert all(entry.note == "" for entry in trace.legend if entry.origin != "negated_goal")


def test_conclusion_is_rendered_in_exam_form_when_proved() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    # Which label lands on which clause follows the canonical input order, so the sentence is
    # built from the legend rather than from hard-coded label names.
    premise_labels = " ∧ ".join(e.label for e in trace.legend if e.origin == "premise")
    goal_label = next(e.label for e in trace.legend if e.origin == "negated_goal")
    assert trace.conclusion == (
        f"{premise_labels} together with {goal_label} is unsatisfiable, "
        "so Mortal(socrates) is proved."
    )


def test_conclusion_recovers_the_goal_by_flipping_the_negated_clause() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    assert "Mortal(socrates)" in trace.conclusion
    assert "¬Mortal(socrates)" not in trace.conclusion


def test_no_exam_conclusion_when_the_search_found_no_proof() -> None:
    """BUDGET_EXHAUSTED has nothing to conclude -- claiming one would be the exact
    "not provable" overreach HLD S18.6 forbids."""
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, Predicate("Zebra", (socrates,)), budget=3)  # type: ignore[arg-type]
    assert CAPTIONED.fol_proof_trace(found).conclusion == ""


# ----------------------------------- refutation tree, plain indented text (item 5, 2026-11-02)


def test_tree_is_rooted_at_the_empty_clause() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    assert trace.tree
    assert trace.tree[0].startswith("□ (empty clause)")
    assert not trace.tree[0].startswith(" ")


def test_tree_indents_each_parent_one_level_deeper() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    depths = [len(line) - len(line.lstrip(" ")) for line in trace.tree]
    assert depths[0] == 0
    assert set(depths) == set(range(0, max(depths) + 1, 2))


def test_tree_names_every_clause_it_shows() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    for line in trace.tree:
        assert any(label in line for label in trace.clauses)


def test_tree_bottoms_out_at_input_clauses() -> None:
    """A leaf of the tree is a clause nothing derived -- a premise or the negated goal."""
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = CAPTIONED.fol_proof_trace(found)
    derived = {step.resolvent for step in trace.steps}
    deepest = max(trace.tree, key=lambda line: len(line) - len(line.lstrip(" ")))
    assert not any(label in deepest for label in derived)


def test_no_tree_when_nothing_was_proved() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, Predicate("Zebra", (socrates,)), budget=3)  # type: ignore[arg-type]
    assert CAPTIONED.fol_proof_trace(found).tree == ()


# ------------------ one deterministic numbering, everywhere (Phase 1 item 2, 2026-11-02)

# Reported as "F8 is the negated goal in one output, F2 in another". Those were two different
# runs of two different code versions; the tests below pin the property that matters -- WITHIN
# one run, every view agrees -- and the ordering rule that makes the numbering readable:
# premises in paragraph order, the negated goal last among the inputs, derived clauses after.


def _ravi_trace():
    from src.core import fol_english as fe

    registry: dict = {}
    premises = [
        fe.parse(s, registry)
        for s in (
            "All students who study pass the exam",
            "Ravi is a student",
            "Ravi studies or Ravi is lucky",
            "Anyone who is lucky passes the exam",
        )
    ]
    goal = fe.parse("Ravi passes the exam", registry)
    return CAPTIONED.fol_proof_trace(fol_prove(premises, goal))


def test_every_label_in_the_tree_is_defined_in_the_legend() -> None:
    trace = _ravi_trace()
    defined = {entry.label for entry in trace.legend}
    for line in trace.tree:
        cited = line.rsplit("(", 1)[1].rstrip(")")
        assert cited in defined


def test_the_tree_and_the_legend_agree_on_each_clause_text() -> None:
    trace = _ravi_trace()
    for line in trace.tree:
        body, cited = line.strip().rsplit("  (", 1)
        assert trace.clauses[cited.rstrip(")")] == body


def test_the_conclusion_cites_the_same_negated_goal_label_as_the_legend() -> None:
    trace = _ravi_trace()
    goal_label = next(e.label for e in trace.legend if e.origin == "negated_goal")
    assert f" {goal_label} " in trace.conclusion
    assert trace.tree[1].strip().endswith(f"({goal_label})")


def test_the_negated_goal_is_the_last_input_clause_not_a_sorted_accident() -> None:
    trace = _ravi_trace()
    inputs = [e for e in trace.legend if e.origin != "derived"]
    assert inputs[-1].origin == "negated_goal"
    assert all(e.origin == "premise" for e in inputs[:-1])


def test_premise_labels_follow_paragraph_order() -> None:
    """F1 is the first sentence's clause, not whichever clause sorted first."""
    trace = _ravi_trace()
    first = next(e for e in trace.legend if e.label == "F1")
    assert "Student" in first.text and "Study" in first.text  # sentence 1's rule clause


def test_inconsistent_premises_are_labeled_premise_not_derived() -> None:
    """Found by the Phase 1 item 3 regression sweep: the INCONSISTENT returns never populated
    `input_clauses`, so a contradictory paragraph's own premises rendered as if the search had
    DERIVED them -- the opposite of what happened, and the one case where "where did this clause
    come from" is the entire point of the message."""
    premises = [human(socrates), FolNot(human(socrates))]
    found = fol_prove(premises, mortal(socrates))
    assert found.outcome is FolProofOutcome.INCONSISTENT
    trace = CAPTIONED.fol_proof_trace(found)
    origins = [entry.origin for entry in trace.legend]
    assert origins.count("premise") == 2
    assert origins.count("derived") == 1  # only the empty clause


def test_inconsistent_has_no_negated_goal_because_it_never_used_one() -> None:
    """The conclusion is never added in phase 1, so claiming a negated-goal clause would be a
    lie about how the contradiction was found."""
    premises = [human(socrates), FolNot(human(socrates))]
    trace = CAPTIONED.fol_proof_trace(fol_prove(premises, mortal(socrates)))
    assert not any(entry.origin == "negated_goal" for entry in trace.legend)


# ------------- translating a typed answer into a real clause (HLD S18.16, 2026-11-02) --------
#
# The reverse of `_clause_variable_names`: raw term strings -> real Variable/Constant objects.
# NOT optional -- `_clause_variable_names` assigns FRESH display letters independently per
# clause, so clause a's "x" and clause b's "x" are usually DIFFERENT internal variables. Treating
# a typed "x" as one global Variable("x") would silently merge two independent variables, an
# unsound comparison the student would never see. A token matching neither clause's own display
# map is a Constant -- never guessed as a variable it is not.


def test_a_term_matching_clause_as_display_name_becomes_that_clauses_variable() -> None:
    a = frozenset({(False, human(x))})  # displays as Human(x)
    typed = parse_clause_text("Human(x)")
    resolved = RENDERER.resolve_typed_clause(typed, a, frozenset())
    (literal,) = resolved
    _polarity, pred = literal
    assert pred.args == (x,)


def test_the_same_display_letter_resolves_to_different_variables_per_clause() -> None:
    """The case the whole two-layer design exists to get right: clause a and clause b both
    display their own variable as "x", but those are DIFFERENT internal Variable objects."""
    y = Variable("y")
    a = frozenset({(False, human(x))})  # displays as Human(x), internal name "x"
    b = frozenset({(False, mortal(y))})  # displays as Mortal(x) too -- render gives it "x" as well
    typed_a = parse_clause_text("Human(x)")
    typed_b = parse_clause_text("Mortal(x)")
    resolved_a = RENDERER.resolve_typed_clause(typed_a, a, frozenset())
    resolved_b = RENDERER.resolve_typed_clause(typed_b, b, frozenset())
    ((_, pred_a),) = resolved_a
    ((_, pred_b),) = resolved_b
    assert pred_a.args == (x,)
    assert pred_b.args == (y,)
    assert pred_a.args != pred_b.args


def test_a_token_matching_neither_clauses_display_name_is_a_constant_not_a_guess() -> None:
    """The core rule under test: unmatched -> Constant, never Variable. "z" is not clause a's own
    display variable ("x"), so it must not be silently treated as one."""
    a = frozenset({(False, human(x))})
    typed = parse_clause_text("Human(z)")
    resolved = RENDERER.resolve_typed_clause(typed, a, frozenset())
    (literal,) = resolved
    _polarity, pred = literal
    assert pred.args == (Constant("z"),)


def test_a_ground_constant_name_is_never_mistaken_for_a_variable() -> None:
    a = frozenset({(True, human(socrates))})
    typed = parse_clause_text("Human(socrates)")
    resolved = RENDERER.resolve_typed_clause(typed, a, frozenset())
    (literal,) = resolved
    _polarity, pred = literal
    assert pred.args == (socrates,)


def test_negation_survives_translation() -> None:
    a = frozenset({(False, human(socrates))})
    typed = parse_clause_text("¬Human(socrates)")
    resolved = RENDERER.resolve_typed_clause(typed, a, frozenset())
    (literal,) = resolved
    polarity, _pred = literal
    assert polarity is False


def test_term_matching_is_case_insensitive_against_the_display_map_only() -> None:
    """Typing "X" for a clause whose own display variable is "x" still resolves to that
    variable -- the display map lookup is case-insensitive, but ONLY there; predicate names
    (tested separately) are never case-folded."""
    a = frozenset({(False, human(x))})
    typed = parse_clause_text("Human(X)")
    resolved = RENDERER.resolve_typed_clause(typed, a, frozenset())
    (literal,) = resolved
    _polarity, pred = literal
    assert pred.args == (x,)


def test_an_empty_typed_clause_translates_to_the_empty_clause() -> None:
    assert RENDERER.resolve_typed_clause((), frozenset(), frozenset()) == frozenset()


def test_both_clauses_variables_are_available_for_matching() -> None:
    """A literal built from clause b's own terms, checked against the (a, b) pair -- clause b's
    display names must be consulted too, not just clause a's."""
    y = Variable("y")
    b = frozenset({(False, mortal(y))})  # displays as Mortal(x)
    typed = parse_clause_text("Mortal(x)")
    resolved = RENDERER.resolve_typed_clause(typed, frozenset(), b)
    (literal,) = resolved
    _polarity, pred = literal
    assert pred.args == (y,)


# ------------------ label <-> clause, one source of truth (Step 3b, 2026-11-02) --------------
#
# The board submits a step by LABEL ("F1", "F2"); the handler needs the real FolClause back to
# validate it. This must be the SAME labeling fol_proof_trace already computes -- a second,
# independent labeling pass would drift from what the student is actually looking at on screen.


def test_clause_by_label_matches_the_trace_legend_exactly() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    by_label = RENDERER.fol_clause_by_label(found)
    assert set(by_label) == set(trace.clauses)


def test_clause_by_label_is_deterministic() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    first = RENDERER.fol_clause_by_label(found)
    second = RENDERER.fol_clause_by_label(found)
    assert first == second


# ------------------- fol_step_outcome / fol_answer_error wording (Step 3b, 2026-11-02) --------

TEXT_FOR_WORDING = {
    "fol_step": {
        "FOL_STEP_NOT_COMPLEMENTARY": "{clause_a} / {clause_b} share no complementary predicate.",
        "FOL_STEP_WRONG_RESOLVENT": (
            "{typed} is not what resolving {clause_a} with {clause_b} gives."
        ),
        "VALID": "valid.",
    },
    "fol_answer": {
        "FOL_ANSWER_MALFORMED": 'could not read "{text}".',
    },
}
WORDED = Renderer(text=TEXT_FOR_WORDING)


def test_fol_step_outcome_fills_both_clause_placeholders() -> None:
    message = WORDED.fol_step_outcome(
        FolStepError.FOL_STEP_NOT_COMPLEMENTARY, clause_a="F1: Human(x)", clause_b="F2: Mortal(x)"
    )
    assert message == "F1: Human(x) / F2: Mortal(x) share no complementary predicate."


def test_fol_step_outcome_fills_the_typed_placeholder_for_wrong_resolvent() -> None:
    message = WORDED.fol_step_outcome(
        FolStepError.FOL_STEP_WRONG_RESOLVENT,
        clause_a="F1: Human(x)",
        clause_b="F2: Mortal(x)",
        typed="Zebra(x)",
    )
    assert message == "Zebra(x) is not what resolving F1: Human(x) with F2: Mortal(x) gives."


def test_fol_step_outcome_none_means_valid() -> None:
    assert WORDED.fol_step_outcome(None, clause_a="F1", clause_b="F2") == "valid."


def test_fol_answer_error_quotes_the_offending_text_verbatim() -> None:
    assert WORDED.fol_answer_error("Study(1x") == 'could not read "Study(1x".'


def test_fol_clause_text_renders_a_clause_like_the_legend_does() -> None:
    clause = frozenset({(True, human(socrates))})
    assert RENDERER.fol_clause_text(clause) == "Human(socrates)"


def test_fol_clause_text_renders_the_empty_clause() -> None:
    assert RENDERER.fol_clause_text(frozenset()) == "□ (empty clause)"


# ------------------------------ fol_unifier_text, fol_step_hint (HLD S18.16.9) -----------------

HINT_TEXT = Renderer(
    text={
        "hint": {
            "HINT_FOL_STEP_1": "resolve {clause_a} with {clause_b}.",
            "HINT_FOL_STEP_2": "resolve {clause_a} with {clause_b}, {unifier}.",
        }
    }
)


def test_fol_unifier_text_matches_the_trace_step_formatting() -> None:
    premises = [ForAll(x, FolImplies(human(x), mortal(x))), human(socrates)]
    found = fol_prove(premises, mortal(socrates))
    trace = RENDERER.fol_proof_trace(found)
    step = trace.steps[0]
    a, b, _resolvent, mgu = found.proof_steps[0]
    assert RENDERER.fol_unifier_text(a, b, mgu) == step.unifier


def test_fol_step_hint_level_1_names_the_clauses_only() -> None:
    message = HINT_TEXT.fol_step_hint(
        1, clause_a="F1: Human(x)", clause_b="F2: Mortal(x)", unifier="where x = a"
    )
    assert message == "resolve F1: Human(x) with F2: Mortal(x)."


def test_fol_step_hint_level_2_adds_the_unifier() -> None:
    message = HINT_TEXT.fol_step_hint(
        2, clause_a="F1: Human(x)", clause_b="F2: Mortal(x)", unifier="where x = socrates"
    )
    assert message == "resolve F1: Human(x) with F2: Mortal(x), where x = socrates."


def test_fol_step_hint_level_3_caps_at_level_2_content() -> None:
    kwargs = {"clause_a": "F1", "clause_b": "F2", "unifier": "no substitution needed"}
    assert HINT_TEXT.fol_step_hint(3, **kwargs) == HINT_TEXT.fol_step_hint(2, **kwargs)
