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

from dataclasses import dataclass

from src.core.entail import Entailment, Verdict
from src.core.fol_search import FolSessionResult
from src.core.logic import Clause, Diagnosis, canonical
from src.core.models import ClauseRec, Fact, Skill, State
from src.core.tutor import Hint


@dataclass(frozen=True)
class Renderer:
    """The message table, with one method per thing the system can tell a student."""

    text: dict[str, dict[str, str]]

    def cli(self, key: str, **values: object) -> str:
        return self.text["cli"][key].format(**values)

    def step(self, found: Diagnosis, productive: bool | None) -> str:
        """A diagnosed step. VALID also reports whether it shortened the proof."""
        if found.code.value != "VALID":
            return self.text["step"][found.code.value].format(
                missing=_literals(found.missing), extra=_literals(found.extra)
            )
        split = {True: "productive", False: "unproductive", None: "unknown"}[productive]
        return self.text["productivity"][split]

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

    def fol_outcome(self, result: FolSessionResult) -> str:
        """What to say about a FOL-mode session's result (HLD S18.6.4, S18.7 Phase 8b).

        `budget_exhausted`/`inconsistent` ignore `{steps}` -- their templates do not use it --
        the same way `claim`/`error` ignore values their own templates have no placeholder for.
        """
        return self.text["fol"][result.outcome.value].format(steps=result.step_count)

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
