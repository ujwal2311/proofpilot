"""A terminal adapter: read a line, call `app`, print. No decisions and no wording.

    python -m src.cli                 # from backend/, a practice session over the bank
    python -m src.cli --own           # type your own paragraph and conclusion
    python -m src.cli --exercise ID   # pin one exercise instead of letting the bands choose
    python -m src.cli --script FILE   # replay newline-separated commands (tests, transcripts)

**The HARD GATE.** Nothing in the API or the frontend may be built until this plays an exercise end
to end, because it proves the thing that matters: the whole tutor works with no web layer at all.
If the CLI needed the server, core would not be pure and the API would not be thin.

Every judgment comes back from `core` and every sentence from `data/messages.yaml` via
`app.render`. What is left here is parsing a command and printing lines, which is why
`test_adapters_hold_no_user_facing_wording` can assert this file contains no sentence at all --
the API adapter is held to the same rule, so the two clients cannot drift apart in what they say.
"""

import sys

from src import app
from src.app.render import clause_text, mastery_text
from src.app.view import Board
from src.core import search, tutor
from src.core.bkt import is_done
from src.core.entail import Verdict
from src.core.logic import diagnose, normalize_literal
from src.core.models import Exercise


class Play:
    """One exercise in progress: the board, the hint level, and the student's mastery."""

    def __init__(self, runtime: app.Runtime, mastery: dict) -> None:
        self.runtime, self.mastery = runtime, mastery
        self.say = runtime.render
        self.hint_level = 0
        self.board = Board()
        self.verdict = Verdict.ENTAILED

    def open(self, exercise: Exercise) -> bool:
        """Analyse and lay out. False when the exercise cannot be played."""
        found = app.prepare(exercise.paragraph, exercise.conclusion)
        print("\n" + "=" * 78)
        for record in found.sentences:
            print(f"{'  ' if record.status == 'ok' else '!!'} {record.text}")
            if record.error_code:
                print(f"     {self.say.error(record.error_code, record.text)}")
        for raw in found.warnings:
            print(f"     {self.say.warning(raw)}")
        if any(record.status != "ok" for record in found.sentences):
            print("\n" + self.say.cli("unplayable"))
            return False

        print("\n" + self.say.cli("facts"))
        for fact in found.facts:
            print(f"  {fact.symbol} = " + " | ".join(f'"{t}"' for _, t in fact.phrases))

        self.verdict = found.entailment.verdict
        for line in self.say.entailment(found.entailment):
            print("\n  " + line)
        if self.verdict is Verdict.INCONSISTENT_PREMISES:
            return False
        if self.verdict is Verdict.NOT_ENTAILED:
            print("  " + self.say.cli("say_no"))
        self.board = Board.of(found)
        self.show_board()
        return True

    def show_board(self) -> None:
        print("\n" + self.say.cli("board"))
        for name, clause in self.board.named.items():
            note = "" if name in self.board.relevant else f"   ({self.say.cli('not_needed')})"
            print(f"  {name}: {clause_text(clause)}{note}")

    def show_mastery(self) -> None:
        print("\n" + self.say.cli("mastery") + mastery_text(self.mastery))

    def score(self, trigger: str) -> None:
        self.mastery = tutor.apply_evidence(
            self.mastery, trigger, self.hint_level > 0, self.runtime.policy, self.runtime.params
        )

    def step(self, command: str) -> bool:
        """One proposed resolution. True once the empty clause is on the board."""
        left, _, right = command.partition("=")
        names = left.split()
        if len(names) != 2 or any(name not in self.board for name in names):
            bad = next((n for n in names if n not in self.board), None)
            print(
                "  "
                + (
                    self.say.cli("unknown_clause", sentence=bad)
                    if bad
                    else self.say.cli("bad_step")
                )
            )
            return False
        try:
            claimed = frozenset(normalize_literal(token) for token in right.split())
        except ValueError as refused:
            print(f"  {refused}")
            return False

        before = self.board.clauses()
        found = diagnose(self.board[names[0]], self.board[names[1]], claimed, before)
        productive = None
        if found.code.value == "VALID":
            # V-2: never search when the truth table already settled that the goal is unreachable.
            if self.verdict is Verdict.ENTAILED:
                productive = search.productive(before, before | {claimed})
            name = self.board.add(claimed)
            self.board.relevant.add(name)
            print(f"  VALID -- {self.say.step(found, productive)}  {name}: {clause_text(claimed)}")
        else:
            print(f"  {found.code.value} -- {self.say.step(found, productive)}")

        self.score(tutor.step_trigger(found.code, productive))
        self.hint_level = 0  # the board moved, so the old hint was about another position
        self.show_board()
        self.show_mastery()
        return search.EMPTY_CLAUSE in self.board.clauses()

    def hint(self) -> None:
        self.hint_level = min(self.hint_level + 1, 3)
        plan = tutor.plan_hint(self.board.clauses(), self.verdict, self.hint_level)
        print(f"  [{plan.code}] {self.say.hint(plan, self.board.names())}")
        self.score("hint")

    def claim(self) -> bool:
        code, message = self.say.claim(self.verdict is not Verdict.ENTAILED)
        print(f"  {code} -- {message}")
        self.score(f"claim_not_provable.{code}")
        self.show_mastery()
        return code == "CLAIM_ACCEPTED"


def read(prompt: str, script: list[str] | None) -> str:
    """One line, from the script when there is one. Keeps the loop identical under test."""
    if script is None:
        return input(prompt)
    line = script.pop(0) if script else "quit"
    print(f"{prompt}{line}")
    return line


def loop(exercise: Exercise, play: Play, script: list[str] | None) -> str:
    """One exercise until it is solved, skipped or abandoned."""
    if not play.open(exercise):
        return "unplayable"
    while True:
        command = read(play.say.cli("prompt"), script).strip()
        if command in ("quit", ""):
            return "quit"
        if command == "skip":
            return "skipped"
        if command == "facts":
            play.show_board()
        elif command == "hint":
            play.hint()
        elif command == "no":
            if play.claim():
                return "claimed"
        elif "=" in command:
            if play.step(command):
                print("\n" + play.say.cli("solved"))
                return "solved"
        else:
            print(play.say.cli("help", commands=play.say.cli("commands")))


def main(argv: list[str]) -> int:
    script = None
    if "--script" in argv:
        text = open(argv[argv.index("--script") + 1], encoding="utf-8").read()
        script = [line for line in text.splitlines() if line.strip()]

    runtime = app.Runtime.load()  # every data file validated before a student can reach it
    mastery = runtime.fresh_mastery()
    print(runtime.render.cli("banner"))

    if "--own" in argv:
        paragraph = read(runtime.render.cli("paragraph"), script)
        conclusion = read(runtime.render.cli("conclusion"), script)
        own = Exercise("own", paragraph, conclusion, runtime.render.cli("own_topic"))
        loop(own, Play(runtime, mastery), script)
        return 0

    # --exercise pins one exercise. It exists so a transcript or a test can target a specific case
    # -- a does-not-follow exercise is in the short band and a student who has just proved
    # something is in the long one -- never to bypass selection.
    pinned = argv[argv.index("--exercise") + 1] if "--exercise" in argv else None
    done: list[str] = []
    while not is_done(mastery, runtime.params):
        exercise = (
            next((e for e in runtime.bank if e.id == pinned), None)
            if pinned
            else tutor.next_exercise(runtime.bank, runtime.bands, mastery, tuple(done))
        )
        if exercise is None:
            break
        print(
            "\n"
            + runtime.render.cli(
                "header",
                exercise=exercise.id,
                topic=exercise.topic,
                band=runtime.bands.get(exercise.id, "?"),
            )
        )
        play = Play(runtime, mastery)
        outcome = loop(exercise, play, script)
        mastery = play.mastery
        done.append(exercise.id)
        if outcome == "quit" or pinned:
            break

    print("\n" + runtime.render.cli("mastery") + mastery_text(mastery))
    if is_done(mastery, runtime.params):
        print("\n" + runtime.render.cli("finished"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
