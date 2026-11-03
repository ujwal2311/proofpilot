"""Turn a core result into the words a student reads. Shared by the CLI and the API.

Core decides WHAT happened -- a `logic.Code`, a `Hint.code`, an `ErrorCode`, a `Verdict`. This
module decides how to SAY it, by filling a template from `data/messages.yaml`. It holds no
decisions of its own: every function here is a lookup plus a `format`.

It exists in one place because the alternative is two. The CLI and the API both report the same
outcomes, so wording in either adapter would be wording the other one disagrees with -- and the
one the student sees would depend on which client they happened to use.

Every lookup is `[]`, never `.get(..., default)`. A missing template must be a crash in the test
suite, not generic text in front of a student: "that step is wrong" instead of "only ONE
complementary pair may be cancelled per step" is the difference between the project's premise
working and not. `app.data.load_messages` checks the whole table at startup so it cannot happen.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from src.core.entail import Entailment, Verdict
from src.core.fol_english import display_term_name
from src.core.fol_models import (
    Constant,
    FolClause,
    FolLiteral,
    FunctionTerm,
    Predicate,
    Substitution,
    Term,
    Variable,
)
from src.core.fol_resolve import canonical_literal
from src.core.fol_search import FolProofOutcome, FolSearchResult, FolSessionResult
from src.core.fol_step import FolStepError, RawLiteral
from src.core.logic import Clause, Diagnosis, canonical
from src.core.models import ClauseRec, Fact, Skill, State
from src.core.tutor import Hint


@dataclass(frozen=True)
class FolTraceStep:
    """One resolution step, by clause LABEL (not the clause itself) -- HLD S18.14."""

    left: str
    right: str
    resolvent: str
    unifier: str = ""  # "x = socrates", or "" when the step substituted nothing


@dataclass(frozen=True)
class FolTraceClause:
    """One labeled clause in the legend, with where it came from.

    `origin` is "premise", "negated_goal" or "derived". The negated goal is called out because a
    refutation only makes sense once a reader sees that the OPPOSITE of the goal was assumed --
    without the tag, that clause reads as just another premise (HLD S18.15.6).
    """

    label: str
    text: str
    origin: str
    note: str = ""  # caption, filled from messages.yaml for the negated goal only


@dataclass(frozen=True)
class FolTrace:
    """Labeled clauses + ordered steps for the Explanation tab's read-only FOL view.

    `clauses` keys are first-appearance order (F1, F2, ...), not canonically sorted -- a reader
    meets the premises first and each derived resolvent as it appears, same order the worked
    examples this traces are modelled on use. Empty for a session with no `proof_steps` (the
    unreachable-in-practice zero-step INCONSISTENT case): nothing to label, nothing to step
    through, and the already-rendered `fol_outcome` message explains why on its own.
    """

    clauses: dict[str, str]
    steps: tuple[FolTraceStep, ...]
    has_unrendered_terms: bool
    # Every clause an examiner needs, inputs first then derived -- including inputs no step used,
    # which `clauses` (built from the steps alone) would omit entirely.
    legend: tuple[FolTraceClause, ...] = ()
    # "F1 and F2 together with F3 is unsatisfiable, so Mortal(socrates) is proved." Empty unless
    # the search actually PROVED the goal -- see fol_proof_trace.
    conclusion: str = ""
    # The refutation drawn as indented text, root (the empty clause) first, each parent two
    # spaces deeper. Plain strings on purpose: a real tree diagram would mean a drawing library
    # and a frontend dependency, for no gain a reader of an exam answer would notice.
    tree: tuple[str, ...] = ()


def _clause_variable_names(clause: FolClause) -> dict[str, str]:
    """Fresh, CLAUSE-LOCAL display names (x, y, z, ...) for this clause's variables.

    `standardize_apart_clauses` (HLD S18.3 step 8) renames every clause's variables to something
    globally unique across the whole proof -- "c0_v0", "c1_v0", ... -- precisely so two different
    clauses' same-looking `x` never collide during resolution. That disambiguation is an internal
    correctness need, not something a student should read; within ONE clause, "x"/"y"/"z" is
    already unambiguous, so each clause gets its own fresh naming here, independent of every
    other clause's.
    """
    seen: dict[str, str] = {}
    display = iter("xyzwuvabcdefghijklmnopqrst")  # far more than this grammar's clauses ever use
    for _, pred in sorted(clause, key=canonical_literal):
        for arg in pred.args:
            _collect_variable_names(arg, seen, display)
    return seen


def _collect_variable_names(term: Term, seen: dict[str, str], display: Iterator[str]) -> None:
    if isinstance(term, Variable):
        if term.name not in seen:
            seen[term.name] = next(display)
    elif isinstance(term, FunctionTerm):
        for arg in term.args:
            _collect_variable_names(arg, seen, display)


def _fol_term_text(term: Term, names: dict[str, str]) -> str:
    """A Skolem term renders in exam notation -- `f1(x)`, `C1` -- via `display_term_name`, the
    same source `fol_english.render` uses so the clause list and the CNF working column can never
    disagree about what a term is called. Never silent: `has_unrendered_terms` (below) flags every
    clause that uses one."""
    if isinstance(term, FunctionTerm):
        inner = ", ".join(_fol_term_text(arg, names) for arg in term.args)
        return f"{display_term_name(term.name)}({inner})"
    if isinstance(term, Variable):
        return names[term.name]
    return display_term_name(term.name)  # Constant


def _fol_literal_text(literal: FolLiteral, names: dict[str, str]) -> str:
    polarity, pred = literal
    args = f"({', '.join(_fol_term_text(arg, names) for arg in pred.args)})" if pred.args else ""
    body = f"{pred.name}{args}"
    return body if polarity else f"¬{body}"


def _fol_tree(steps: tuple[FolTraceStep, ...], clauses: dict[str, str]) -> tuple[str, ...]:
    """The derivation as indented text, root first, each parent one level deeper.

    Reads the parent links straight off the step list: a label that no step produced is a leaf
    (a premise or the negated goal), which is where a branch stops. The derivation is a DAG whose
    parents are always earlier steps, so this terminates; a clause used by two branches is simply
    printed under each, the way a hand-drawn refutation tree repeats it.
    """
    produced_by = {step.resolvent: step for step in steps}
    lines: list[str] = []

    def draw(label: str, depth: int) -> None:
        lines.append(f"{'  ' * depth}{clauses[label]}  ({label})")
        step = produced_by.get(label)
        if step is not None:
            draw(step.left, depth + 1)
            draw(step.right, depth + 1)

    draw(steps[-1].resolvent, 0)
    return tuple(lines)


def _fol_unifier_text(left: FolClause, right: FolClause, subst: Substitution) -> str:
    """The step's substitution, e.g. "x = socrates", or "" if nothing was substituted.

    Each variable is shown under ITS OWN parent clause's display naming, the same naming the
    legend used to print that clause -- looking the name up in a combined naming of both parents
    would let the trace say "y = bob" about a clause the reader just saw written with an "x".
    """
    if not subst:
        return ""
    left_names, right_names = _clause_variable_names(left), _clause_variable_names(right)
    parts = []
    for var_name in sorted(subst):
        names = left_names if var_name in left_names else right_names
        parts.append(f"{names.get(var_name, var_name)} = {_fol_term_text(subst[var_name], names)}")
    return ", ".join(parts)


def _label_clauses(result: FolSearchResult) -> tuple[dict[FolClause, str], dict[FolClause, str]]:
    """(clause -> "F1".., clause -> origin). Inputs first, in the order the search received them
    (premises then the negated goal -- the order a worked example uses), then derived clauses in
    derivation order. The ONE labeling pass `fol_proof_trace` and `fol_clause_by_label` both read,
    so the board a student sees and the clause a submitted label resolves to can never disagree.
    """
    labels: dict[FolClause, str] = {}
    origins: dict[FolClause, str] = {}

    def label(clause: FolClause) -> str:
        if clause not in labels:
            labels[clause] = f"F{len(labels) + 1}"
        return labels[clause]

    for clause, origin in result.input_clauses:
        origins[clause] = origin
        label(clause)
    for a, b, resolvent, _mgu in result.proof_steps:
        label(a)
        label(b)
        label(resolvent)
    return labels, origins


def _fol_goal_text(result: FolSearchResult) -> str:
    """The goal, recovered by un-negating the negated-goal clause.

    The goal formula itself never reaches this layer -- `fol_prove` only keeps clauses -- but the
    negated goal of an atomic conclusion is exactly one clause holding exactly one literal, so
    flipping that literal's polarity returns the goal verbatim. Anything else (a conjunctive or
    quantified conclusion, which clausifies into several literals) is not reconstructible without
    guessing, so it falls back to a neutral phrase rather than inventing one.
    """
    goal_clauses = [clause for clause, origin in result.input_clauses if origin == "negated_goal"]
    if len(goal_clauses) == 1 and len(goal_clauses[0]) == 1:
        polarity, predicate = next(iter(goal_clauses[0]))
        return _fol_literal_text((not polarity, predicate), _clause_variable_names(goal_clauses[0]))
    return "the conclusion"


def _fol_clause_text(clause: FolClause) -> str:
    """One clause, canonically ordered (by `canonical_literal`, not display text -- rule 4). The
    empty clause is `□`, the worked-example notation, matching the goal of a FOL proof -- not
    `clause_text`'s `[]` (propositional) or `clause_english`'s "a contradiction" (prose); FOL's
    own convention, deliberately distinct from both. The symbol is NAMED rather than left bare:
    a student meeting `□` for the first time has no way to read it, and the whole point of the
    derivation is that reaching it is what proves the goal (2026-11-02)."""
    if not clause:
        return "□ (empty clause)"
    names = _clause_variable_names(clause)
    ordered = sorted(clause, key=canonical_literal)
    return " ∨ ".join(_fol_literal_text(literal, names) for literal in ordered)


def _has_function_term(term: Term) -> bool:
    if isinstance(term, FunctionTerm):
        return True
    return False  # Variable / Constant are leaves, never contain a further term


def _clause_has_function_term(clause: FolClause) -> bool:
    return any(_has_function_term(arg) for _, pred in clause for arg in pred.args)


@dataclass(frozen=True)
class Renderer:
    """The message table, with one method per thing the system can tell a student."""

    text: dict[str, dict[str, str]]

    def cli(self, key: str, **values: object) -> str:
        return self.text["cli"][key].format(**values)

    def step(self, found: Diagnosis, productive: bool | None) -> str:
        """A diagnosed step. VALID also reports whether it shortened the proof.

        `step.VALID`'s own text ("valid.") was defined but never read here, found live -- the
        rendered banner was just the productivity clause on its own ("that shortens the proof."),
        missing its verb. The two are meant to read as one sentence, same as every other code's
        messages.yaml text continues after that code's name.
        """
        if found.code.value != "VALID":
            return self.text["step"][found.code.value].format(
                missing=_literals(found.missing), extra=_literals(found.extra)
            )
        split = {True: "productive", False: "unproductive", None: "unknown"}[productive]
        return f"{self.text['step']['VALID']} {self.text['productivity'][split]}"

    def hint(self, plan: Hint, names: dict[Clause, str]) -> str:
        """A hint, filled only with what its level revealed.

        `names` maps a clause to its board id. The hint carries at most two parents and, at level
        3, the resolvent -- so a template cannot render more than the level earned even if it
        tried, because the value is not in the object.
        """
        return self.text["hint"][plan.code].format(
            clauses=", ".join(names.get(clause, "?") for clause in plan.clauses),
            resolvent=clause_text(plan.resolvent) if plan.resolvent is not None else "",
        )

    def claim(self, accepted: bool) -> tuple[str, str]:
        """(code, message) for a `does not follow` claim."""
        code = "CLAIM_ACCEPTED" if accepted else "CLAIM_REJECTED"
        return code, self.text["claim"][code]

    def entailment(self, found: Entailment) -> list[str]:
        """What to say about the verdict, and nothing more.

        An ENTAILED verdict returns NOTHING on purpose. Announcing "it does follow" would be a
        spoiler: `claim_not_provable` is a scored action (section 9), and a student told the
        answer cannot be assessed on deciding it. A first draft printed all three verdicts and
        gave the answer away on every entailed exercise.
        """
        if found.verdict is Verdict.ENTAILED:
            return []
        lines = [self.text["entailment"][found.verdict.name]]
        if found.counterexample is not None:
            row = ", ".join(
                f"{s}={'T' if v else 'F'}" for s, v in sorted(found.counterexample.items())
            )
            lines.append(self.text["entailment"]["counterexample"].format(row=row))
        return lines

    def error(self, code: str, sentence: str = "") -> str:
        return self.text["error"][code].format(sentence=sentence)

    def sentence_errors(self, sentences: "tuple") -> dict[str, str]:
        """{sentence id: rendered refusal} for every REFUSED sentence -- the web UI's own version
        of what `error()` already gives the CLI (2026-11-02). No new wording: reuses `error()`
        and the existing `error:` messages.yaml section exactly, for propositional and FOL
        refusals alike -- `SentenceRec.error_code` is always one of `core.english`'s own codes
        regardless of `logic_mode` (a FOL-specific code never reaches this field today).
        """
        return {rec.id: self.error(rec.error_code, rec.text) for rec in sentences if rec.error_code}

    def fol_outcome(self, result: FolSessionResult) -> str:
        """What to say about a FOL-mode session's result (HLD S18.6.4, S18.7 Phase 8b).

        `budget_exhausted`/`inconsistent` ignore `{steps}` -- their templates do not use it --
        the same way `claim`/`error` ignore values their own templates have no placeholder for.
        """
        return self.text["fol"][result.outcome.value].format(steps=result.step_count)

    def resolve_typed_clause(
        self, raw: tuple[RawLiteral, ...], a: FolClause, b: FolClause
    ) -> FolClause:
        """A student's syntactically-parsed answer (`core.fol_step.parse_clause_text`) -> a real
        `FolClause`, using clause `a`'s then `b`'s own per-clause display naming to decide which
        raw term tokens are Variables.

        NOT OPTIONAL: `_clause_variable_names` assigns fresh display letters INDEPENDENTLY per
        clause (HLD S18.14.2) -- clause `a`'s "x" and clause `b`'s "x" are usually different
        internal `Variable` objects. Treating a typed "x" as one global `Variable("x")` would
        silently merge two independent variables, an unsound comparison the student would never
        see. A token in neither clause's own display map is a `Constant` -- never guessed as a
        variable it is not. The display lookup is case-insensitive (so "X" matches a shown "x");
        predicate names are matched exactly as typed, never folded.
        """
        display = {name.lower(): var for var, name in _clause_variable_names(a).items()}
        display |= {name.lower(): var for var, name in _clause_variable_names(b).items()}

        def term(token: str) -> Term:
            internal = display.get(token.lower())
            return Variable(internal) if internal is not None else Constant(token.lower())

        return frozenset(
            (not negated, Predicate(name, tuple(term(arg) for arg in args)))
            for negated, name, args in raw
        )

    def fol_step_outcome(
        self,
        code: FolStepError | None,
        *,
        clause_a: str,
        clause_b: str,
        typed: str = "",
    ) -> str:
        """The student-facing sentence for one submitted FOL step (HLD S18.16.3).

        `code=None` means VALID, same convention `fol_claim_accepted`/`fol_hint_code` use
        elsewhere for "nothing is wrong here". `clause_a`/`clause_b` are pre-rendered, labeled
        clause text (e.g. "F1: Human(x)"); `typed` is the student's own answer, rendered the same
        way -- only `FOL_STEP_WRONG_RESOLVENT`'s template uses it, so it is optional everywhere
        else, the same pattern `fol_outcome`'s `{steps}` already uses for a template-specific
        placeholder.
        """
        key = code.value if code is not None else "VALID"
        return self.text["fol_step"][key].format(clause_a=clause_a, clause_b=clause_b, typed=typed)

    def fol_answer_error(self, text: str) -> str:
        """The student-facing sentence for a FOL answer that could not even be parsed (HLD
        S18.16, `core.fol_step.FolAnswerSyntaxError`). `text` is the exact string the student
        typed, quoted verbatim in the template so a typo is visibly a typo."""
        return self.text["fol_answer"]["FOL_ANSWER_MALFORMED"].format(text=text)

    def fol_clause_text(self, clause: FolClause) -> str:
        """One clause's literal text, the same rendering the legend uses, for a caller that has
        a `FolClause` but no proof-wide labeling to look it up through (HLD S18.16's step
        handler, which renders a clause BEFORE knowing whether it is even a legal resolvent)."""
        return _fol_clause_text(clause)

    def fol_unifier_text(self, left: FolClause, right: FolClause, subst: Substitution) -> str:
        """A step's substitution, the exact text the trace already shows for it -- public so the
        hint ladder (HLD S18.16.9) can describe a step BEFORE it is a `FolTraceStep`, using the
        same wording, not a second phrasing of the same fact."""
        return _fol_unifier_text(left, right, subst)

    def fol_step_hint(self, level: int, *, clause_a: str, clause_b: str, unifier: str) -> str:
        """The step-level FOL hint at `level` (HLD S18.16.9) -- level 1 names the two clauses,
        level 2 adds the unifier. FOL has only two levels; `level >= 2` all render level 2's
        content, since there is nothing further this ladder reveals."""
        key = "HINT_FOL_STEP_1" if level <= 1 else "HINT_FOL_STEP_2"
        return self.text["hint"][key].format(clause_a=clause_a, clause_b=clause_b, unifier=unifier)

    def fol_clause_by_label(self, result: FolSearchResult) -> dict[str, FolClause]:
        """ "F1" -> the real `FolClause` it labels -- the reverse of `fol_proof_trace`'s own
        labeling, for the step-submission handler (HLD S18.16), which needs the actual clause a
        student's chosen label refers to, not just its rendered text.

        Built from the SAME `_label_clauses` pass `fol_proof_trace` uses, never a second,
        independent labeling -- two labeling passes over the same result could assign different
        labels to the same clause if their iteration ever diverged, which would let a student's
        board (built from one pass) disagree with what this validates (the other).
        """
        labels, _origins = _label_clauses(result)
        return {label: clause for clause, label in labels.items()}

    def fol_proof_trace(self, result: FolSearchResult) -> FolTrace:
        """Label every clause `result.proof_steps` mentions and render the step list (HLD
        S18.14). No yaml lookup -- the trace is pure structure; `fol_outcome` above already says
        what it MEANS (proved / budget-exhausted / inconsistent), so this never repeats that.

        Takes `FolSearchResult`, not the `FolSessionResult` that lives on `State` -- a `Predicate`
        contains a recursive `Term` union (`FunctionTerm.args: tuple[Term, ...]`), and
        `test_every_state_field_is_json_representable` doesn't just fail on that, it crashes with
        `RecursionError` (confirmed directly, not assumed). `FolSessionResult` stays exactly
        outcome+step_count; the raw trace is recomputed at the API edge, per request, never
        persisted -- the same ephemeral treatment `fol_message` already gets.
        """
        labels, origins = _label_clauses(result)
        steps = tuple(
            FolTraceStep(labels[a], labels[b], labels[resolvent], _fol_unifier_text(a, b, mgu))
            for a, b, resolvent, mgu in result.proof_steps
        )
        clauses = {text: _fol_clause_text(clause) for clause, text in labels.items()}
        caption = self.text.get("fol", {}).get("negated_goal", "")
        legend = tuple(
            FolTraceClause(
                text,
                clauses[text],
                origins.get(clause, "derived"),
                caption if origins.get(clause) == "negated_goal" else "",
            )
            for clause, text in labels.items()
        )
        has_unrendered = any(_clause_has_function_term(clause) for clause in labels)
        return FolTrace(
            clauses,
            steps,
            has_unrendered,
            legend,
            self._fol_conclusion(result, legend),
            _fol_tree(steps, clauses) if result.proof_steps else (),
        )

    def _fol_conclusion(self, result: FolSearchResult, legend: tuple[FolTraceClause, ...]) -> str:
        """The refutation restated the way an exam answer ends, or "" if nothing was proved.

        Only PROVED earns a conclusion. BUDGET_EXHAUSTED has nothing to conclude and INCONSISTENT
        is already explained by `fol_outcome`'s own wording -- asserting a conclusion for either
        would be the "not provable" overreach HLD section 18.6 exists to prevent.
        """
        template = self.text.get("fol", {}).get("conclusion_proved", "")
        if result.outcome is not FolProofOutcome.PROVED or not template:
            return ""
        premises = [entry.label for entry in legend if entry.origin == "premise"]
        negated = [entry for entry in legend if entry.origin == "negated_goal"]
        if not premises or len(negated) != 1:
            return ""
        return template.format(
            premises=" ∧ ".join(premises),
            negated=negated[0].label,
            goal=_fol_goal_text(result),
        )

    def warning(self, raw: str) -> str:
        """Core emits `CODE: detail`; the code selects the wording and the detail fills it."""
        code, _, detail = raw.partition(": ")
        return self.text["warning"][code].format(phrase=detail)


def clause_text(clause: Clause) -> str:
    """One clause, canonically ordered. The empty clause is `[]`, which is the goal of a proof."""
    return " v ".join(canonical(clause)) or "[]"


def clause_english(clause: ClauseRec, facts: tuple[Fact, ...]) -> str:
    """One board clause in the student's own words -- built ONLY from phrases they confirmed.

    Each literal's symbol is looked up against `facts` (never guessed): a missing symbol is a
    data-integrity bug and crashes here rather than inventing wording for it, same discipline as
    every other lookup in this module. A fact's FIRST phrase is used when several were merged
    into one symbol, since that is the phrase order the student's own paragraph established.
    General over any clause the resolution process can produce -- nothing here names a symbol or
    an exercise.
    """
    if not clause.literals:
        return "a contradiction"
    text_of = {fact.symbol: fact.phrases[0][1] for fact in facts}
    parts = []
    for literal in clause.literals:
        negated = literal.startswith("~")
        phrase = text_of[literal[1:] if negated else literal]
        parts.append(f"not {phrase}" if negated else phrase)
    return " or ".join(parts)


def clause_english_map(state: State) -> dict[str, str]:
    """Every board clause's English, keyed by id -- what the Prove screen's sidebar renders."""
    return {clause.id: clause_english(clause, state.facts) for clause in state.clauses}


def _literals(clause: Clause) -> str:
    return ", ".join(canonical(clause)) or "-"


def mastery_text(mastery: dict[Skill, float]) -> str:
    """A bar per skill. Iterates the mapping, so M1's three and M2's four both render."""
    return "  ".join(
        f"{skill.value} {'#' * round(value * 10):<10} {value:.0%}"
        for skill, value in mastery.items()
    )
