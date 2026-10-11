"""The HARD CLI GATE: the whole tutor works with no web layer at all (HLD section 4).

Nothing in the API or the frontend may be built until these pass, and the reason is structural
rather than procedural. If the CLI can play a full exercise, then core is genuinely pure, the §7
ordering lives in one place, and the API has nothing left to be except a transport. If it cannot,
then logic has leaked into the edge and no amount of API testing would show it.

Every test here drives `src.cli.main` through `--script`, which reads commands from a file instead
of a terminal. That keeps the loop under test IDENTICAL to the interactive one -- a test that
called the internals would pass while the actual command loop was broken.
"""

import re
import sys
from pathlib import Path

from src import cli
from src.app.data import load_bank, load_messages
from src.core.bkt import BktParams
from src.core.models import Skill

ROOT = Path(__file__).resolve().parents[2]
BANK, META = load_bank()
PARAMS = BktParams.from_config()
# User-facing prose lives in data/messages.yaml (HLD section 4.1), so expectations are read from
# there rather than quoted. These tests check the WIRING -- right code, right template, right
# values -- not the wording, which humans will review and edit.
TEXT = load_messages()


def run(commands: str, *flags: str, tmp_path: Path, capsys) -> str:
    """Drive the real command loop and return everything it printed.

    `capsys` is threaded through explicitly rather than read in an autouse fixture: a fixture
    only sees the output AFTER the test body, so the first version returned the PREVIOUS test's
    text and nineteen assertions failed on output they never produced.
    """
    script = tmp_path / "script.txt"
    script.write_text(commands, encoding="utf-8")
    assert cli.main(["--script", str(script), *flags]) == 0
    return capsys.readouterr().out


# ============================================================ the gate: a full exercise, solved


def test_the_cli_plays_an_exercise_from_paragraph_to_empty_clause(tmp_path: Path, capsys) -> None:
    out = run("c1 c2 = B\nc3 c4 =\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "A = " in out and "B = " in out, "the facts must be shown before proving"
    assert out.count("VALID") == 2
    assert TEXT["cli"]["solved"] in out


def test_a_solved_exercise_raises_every_tracked_skill(tmp_path: Path, capsys) -> None:
    out = run("c1 c2 = B\nc3 c4 =\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    # The mastery bar is rendered as a percentage; the prior is 30%, so every skill must have moved
    # up by the end. A proof that teaches nothing is a proof the tutor did not notice.
    assert "30%" not in out.split("EMPTY CLAUSE")[0].split("board:")[-1]
    for skill in (Skill.CLASH, Skill.RESOLVE, Skill.STRATEGY):
        assert skill.value in out


# ================================================================ a deliberate mistake, named


def test_a_step_with_no_clash_is_named_not_merely_rejected(tmp_path: Path, capsys) -> None:
    # The deliberate mistake the transcript records. The student must be told WHICH mistake they
    # made -- "wrong" teaches nothing, and naming it is the whole formative premise.
    out = run("c2 c3 = A\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "NO_CLASH" in out
    assert TEXT["step"]["NO_CLASH"] in out


def test_a_wrong_resolvent_says_what_is_missing_and_what_is_extra(tmp_path: Path, capsys) -> None:
    out = run("c1 c2 = A\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "WRONG_RESOLVENT" in out
    assert "missing" in out and "extra" in out  # the template's two placeholders, both filled


def test_a_duplicate_step_is_named(tmp_path: Path, capsys) -> None:
    out = run("c1 c2 = B\nc1 c2 = B\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "DUPLICATE" in out


def test_an_unknown_clause_name_is_refused_with_the_board_listed(tmp_path: Path, capsys) -> None:
    # A typo must not look like a logical mistake, and it must not be scored as one.
    out = run("c1 c9 = B\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert TEXT["cli"]["unknown_clause"].format(sentence="c9") in out
    assert "NO_CLASH" not in out and "WRONG_RESOLVENT" not in out


def test_a_malformed_step_explains_the_syntax(tmp_path: Path, capsys) -> None:
    out = run("c1 = B\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert TEXT["cli"]["bad_step"] in out


# ======================================================================= hints, levels 1 to 3


def test_the_hint_ladder_escalates_and_only_level_three_gives_the_step(
    tmp_path: Path, capsys
) -> None:
    out = run("hint\nhint\nhint\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "[HINT_1]" in out and "[HINT_2]" in out and "[HINT_3]" in out
    assert out.index("[HINT_1]") < out.index("[HINT_2]") < out.index("[HINT_3]")
    # Level 1 names one clause, level 2 names two, level 3 hands over the resolvent. The resolvent
    # must appear ONLY after level 3 -- it is the payload, not the rendering, that holds it back.
    before_three = out[: out.index("[HINT_3]")]
    assert "to get" not in before_three, "a hint before level 3 revealed the resolvent"
    assert "to get" in out[out.index("[HINT_3]") :]


def test_a_hint_then_a_correct_step_is_scored_as_hinted(tmp_path: Path, capsys) -> None:
    """The BKT hint rule, visible end to end (HLD section 9).

    A correct step after a hint must score LOWER than the same step without one, or asking for
    help would be free and the ladder would be pure gain.
    """
    clean = run("c1 c2 = B\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    hinted = run("hint\nc1 c2 = B\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)

    def clash_pct(text: str) -> int:
        return int(text.rsplit("CLASH", 1)[1].split("%")[0].split()[-1])

    assert clash_pct(hinted) < clash_pct(clean), "a hinted step was not penalised"


def test_adding_a_clause_resets_the_ladder_so_the_next_step_is_unhinted(
    tmp_path: Path, capsys
) -> None:
    # The board moved, so the old hint was about a position that no longer exists. Charging the
    # next step as hinted would punish the student for help they did not get.
    out = run("hint\nc1 c2 = B\nhint\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert out.count("[HINT_1]") == 2, "the ladder did not restart after the board changed"


# ========================================================= the does-not-follow exercise (V-2)


def test_the_cli_plays_a_does_not_follow_exercise_and_accepts_the_claim(
    tmp_path: Path, capsys
) -> None:
    # Expected wording is READ FROM messages.yaml, not quoted here. The prose is data now (HLD
    # section 4.1) and a human will review and edit it; a test that pinned the exact sentence
    # would make every wording improvement look like a regression. What is asserted is the
    # WIRING: that the right code produced the right template, filled with the right values.
    out = run("no\n", "--exercise", "ex-11", tmp_path=tmp_path, capsys=capsys)
    assert TEXT["entailment"]["NOT_ENTAILED"] in out
    assert "CLAIM_ACCEPTED" in out
    assert TEXT["claim"]["CLAIM_ACCEPTED"] in out
    assert "A=F" in out or "A=T" in out, "the counterexample row must be shown"


def test_the_not_follow_ladder_is_used_instead_of_the_proof_ladder(tmp_path: Path, capsys) -> None:
    out = run("hint\nhint\nhint\n", "--exercise", "ex-11", tmp_path=tmp_path, capsys=capsys)
    for level in (1, 2, 3):
        assert f"[HINT_NOT_FOLLOW_{level}]" in out
    assert "[HINT_1]" not in out, "a non-entailing exercise must not use the proof ladder"
    # Levels 1 and 2 describe the METHOD; only level 3 gives the verdict away. Compared against
    # the templates rather than against quoted prose.
    giveaway = TEXT["hint"]["HINT_NOT_FOLLOW_3"]
    assert giveaway in out[out.index("[HINT_NOT_FOLLOW_3]") :]
    assert giveaway not in out[: out.index("[HINT_NOT_FOLLOW_3]")]


def test_claiming_not_provable_on_a_provable_exercise_is_rejected(tmp_path: Path, capsys) -> None:
    out = run("no\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert "CLAIM_REJECTED" in out
    assert TEXT["claim"]["CLAIM_REJECTED"] in out


def test_no_search_runs_on_a_does_not_follow_exercise(tmp_path: Path, monkeypatch, capsys) -> None:
    """V-2 again, this time through the CLI (HLD section 6.6).

    The core-level test proves `tutor.plan_hint` does not search. This proves the EDGE does not
    search either -- the CLI calls `search.productive` itself when a step is valid, so it has its
    own chance to get this wrong, and a whole-space BFS on every hint is exactly the defect the
    short-circuit was added to fix.
    """
    calls = []
    for name in ("distance", "best_next_step", "productive"):
        original = getattr(cli.search, name)
        monkeypatch.setattr(
            cli.search,
            name,
            lambda *a, _o=original, _n=name, **k: (calls.append(_n), _o(*a, **k))[1],
        )
    run("hint\nhint\nhint\nno\n", "--exercise", "ex-11", tmp_path=tmp_path, capsys=capsys)
    assert calls == [], f"V-2 violated from the CLI: {calls}"


# =================================================================== own-question mode, and data


def test_own_question_mode_runs_the_same_pipeline(tmp_path: Path, capsys) -> None:
    out = run(
        "If the bell rings then the class ends. The bell rings.\n"
        "The class ends.\nc1 c2 = B\nc3 c4 =\n",
        "--own",
        tmp_path=tmp_path,
        capsys=capsys,
    )
    assert "EMPTY CLAUSE" in out


def test_own_question_mode_normalizes_exactly_like_the_bank(tmp_path: Path, capsys) -> None:
    """Sprint addendum 1: the CLI is an entry point, so messy input must give the same answer.

    This is the route the S2 bug would have reached a student by: the CLI reads two separate
    strings from a human who may or may not type a full stop.
    """
    tidy = run(
        "If the bell rings then the class ends. The bell rings.\nThe class ends.\nfacts\n",
        "--own",
        tmp_path=tmp_path,
        capsys=capsys,
    )
    messy = run(
        "\n  IF the bell rings THEN the class ends.  The bell rings!  \n\n"
        "the class ends. ! ?  \nfacts\n",
        "--own",
        tmp_path=tmp_path,
        capsys=capsys,
    )
    assert _board(tidy) == _board(messy), "the CLI normalized its two inputs differently"
    assert _facts(tidy) == _facts(messy)


# Matched by SHAPE, not by first letter. The first version used startswith("c") and picked up the
# echoed prompt line "conclusion: ...", which differs between the two runs on purpose -- the CLI
# echoes what the student typed. The BOARD is the thing that has to be identical.
_BOARD_LINE = re.compile(r"^\s*~?c\d+: ")


def _board(text: str) -> list[str]:
    return sorted(line.strip() for line in text.splitlines() if _BOARD_LINE.match(line))


def _facts(text: str) -> list[str]:
    return sorted(line.strip() for line in text.splitlines() if ' = "' in line)


def test_an_unparseable_own_question_is_refused_not_guessed(tmp_path: Path, capsys) -> None:
    out = run("Every student passes.\nThe class ends.\n", "--own", tmp_path=tmp_path, capsys=capsys)
    assert TEXT["error"]["QUANTIFIER_UNSUPPORTED"] in out, "the refusal must carry its hint"
    assert TEXT["cli"]["unplayable"] in out
    assert TEXT["cli"]["board"] not in out, "a refused exercise must not lay out a board"


# ================================================================== the session loop itself


def test_the_session_offers_a_new_exercise_after_one_is_solved(tmp_path: Path, capsys) -> None:
    out = run("c1 c2 = B\nc3 c4 =\nquit\n", tmp_path=tmp_path, capsys=capsys)
    offered = [line for line in out.splitlines() if line.startswith("[ex-")]
    assert len(offered) >= 2, f"only {offered} were offered"
    assert offered[0].startswith("[ex-01"), "the first unseen short exercise comes first"


def test_the_session_shows_the_band_it_chose(tmp_path: Path, capsys) -> None:
    out = run("quit\n", tmp_path=tmp_path, capsys=capsys)
    header = next(line for line in out.splitlines() if line.startswith("[ex-"))
    assert any(band in header for band in ("short", "medium", "long")), header


def test_skip_moves_on_without_scoring(tmp_path: Path, capsys) -> None:
    out = run("skip\nskip\nquit\n", tmp_path=tmp_path, capsys=capsys)
    assert len([line for line in out.splitlines() if line.startswith("[ex-")]) >= 2
    assert "VALID" not in out and "CLAIM_" not in out


def test_an_empty_command_leaves_and_an_unknown_one_shows_help(tmp_path: Path, capsys) -> None:
    out = run("what\nquit\n", "--exercise", "ex-01", tmp_path=tmp_path, capsys=capsys)
    assert TEXT["cli"]["commands"].strip().splitlines()[0] in out


def test_relevance_is_shown_but_nothing_is_deleted(tmp_path: Path, capsys) -> None:
    # Section 6.5: the filter REPORTS what the conclusion cannot reach; the student may still use
    # any clause. A CLI that hid the distractors would be teaching a different exercise.
    out = run("facts\n", "--exercise", "ex-08", tmp_path=tmp_path, capsys=capsys)
    board = [line for line in out.splitlines() if _BOARD_LINE.match(line)]
    marked = [line for line in board if TEXT["cli"]["not_needed"] in line]
    assert marked, "no clause was marked as not needed for this conclusion"
    assert len(marked) < len(board), "every clause was marked irrelevant"


def test_the_cli_imports_no_web_framework() -> None:
    # The gate, stated as a property rather than a claim: this module may not reach for fastapi,
    # and it must drive core directly (HLD section 4).
    import ast

    tree = ast.parse(Path(cli.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {"fastapi", "pydantic", "uvicorn", "httpx", "requests"}
    assert "src" in {name for name in imported} or any(m.startswith("src") for m in imported), (
        "the CLI must drive core directly"
    )


def test_the_cli_is_runnable_as_a_module() -> None:
    # `python -m src.cli` is the documented command, and `__main__` guards are exactly the kind
    # of thing that works until someone moves a file.
    import subprocess

    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "--exercise",
            "ex-01",
            "--script",
            str(ROOT / "README.md"),
        ],
        capture_output=True,
        cwd=ROOT / "backend",
    )
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    assert b"board:" in done.stdout
