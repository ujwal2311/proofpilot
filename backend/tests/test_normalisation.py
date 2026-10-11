"""ONE preparation function for every entry point (sprint addendum 1).

Text reaches core by several routes -- a bank paragraph, a bank conclusion, a CLI prompt, an
`/api/parse` body, a held-out paragraph, and in M2 a typed formula. Every one of them must go
through `english.prepare`, and this file is what makes that a rule rather than an intention.

WHY IT IS A RULE. The conclusion used to be handed to the parser raw while the paragraph went
through the splitter. A trailing full stop therefore survived on the conclusion only, so
"we get wet." and "we get wet" became two different facts and the worked example in the design
review stopped following from its own premises. No unit test on any single module could see it:
each module was correct, and the two callers disagreed.

HOW IT IS TESTED. One messy transformation of a clean input -- trailing ". ! ?", curly quotes and
apostrophes, doubled spaces, uppercase keywords, a leading and trailing newline -- fed through
every entry point, asserting the SAME facts and the SAME verdict as the clean version. Not "it
doesn't crash": identical results, because a silently different answer is the failure mode.

This file grows as S4 and S6 add entry points. `ENTRY_POINTS` is the list, and
`test_every_known_entry_point_is_covered` fails if a route is added to the system without being
added here.
"""

import ast
from pathlib import Path

import pytest
from src.core import session
from src.core.english import prepare
from src.core.logic import canonical

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "backend" / "src" / "core"

CLEAN_PARAGRAPH = "Either the oven works or the bread is bought. The oven does not work."
CLEAN_CONCLUSION = "The bread is bought."


def messy(text: str) -> str:
    """Everything a word processor, a phone keyboard or a hurried student does to a paragraph."""
    return (
        "\n  "
        + text.replace("Either", "EITHER")
        .replace(" or ", " OR ")
        .replace("does not", "DOES NOT")
        .replace(" the ", "  the ")  # doubled spaces
        .replace(".", ". ")
        .rstrip()
        .rstrip(".")
        + ". ! ?  \n"
    )


MESSY_PARAGRAPH = messy(CLEAN_PARAGRAPH)
MESSY_CONCLUSION = messy(CLEAN_CONCLUSION)

# Curly punctuation is a separate case: it must survive INSIDE a contraction, because a curly
# apostrophe that reaches the contraction table turns "isn't" into a content word and the
# negation is lost on the way to facts.py.
CLEAN_CONTRACTED = "Either the oven works or the bread is bought. The oven isn't working."
CURLY_CONTRACTED = "Either the oven works or the bread is bought. The oven isn’t working."


def fingerprint(paragraph: str, conclusion: str) -> tuple:
    """What the student actually ends up being taught: the facts, the clauses and the verdict."""
    found = session.analyse(paragraph, conclusion)
    return (
        tuple((f.symbol, tuple(text for _, text in f.phrases)) for f in found.facts),
        tuple(sorted(canonical(c) for c in found.kb)),
        tuple(canonical(c) for c in found.goal),
        found.entailment.verdict.name,
        tuple(r.status for r in found.sentences),
    )


# =========================================================== every entry point, same answer

# Each entry is (name, callable taking (paragraph, conclusion) and returning a fingerprint).
# S4 adds the API body, S6 the typed formula. A route added to the system and not added here
# fails `test_every_known_entry_point_is_covered`.
ENTRY_POINTS = {
    "session.analyse": fingerprint,
}


@pytest.mark.parametrize("name", sorted(ENTRY_POINTS))
def test_messy_input_gives_the_same_answer_as_clean_input(name: str) -> None:
    through = ENTRY_POINTS[name]
    assert through(MESSY_PARAGRAPH, MESSY_CONCLUSION) == through(
        CLEAN_PARAGRAPH, CLEAN_CONCLUSION
    ), f"{name}: messy input produced a DIFFERENT answer, not merely a different string"


@pytest.mark.parametrize("name", sorted(ENTRY_POINTS))
def test_a_curly_apostrophe_still_negates(name: str) -> None:
    through = ENTRY_POINTS[name]
    assert through(CURLY_CONTRACTED, CLEAN_CONCLUSION) == through(
        CLEAN_CONTRACTED, CLEAN_CONCLUSION
    )


def test_the_messy_fixture_is_actually_messy() -> None:
    # A fixture that is accidentally identical to the clean input would make every test above
    # pass for no reason. The transformation has to be real.
    assert MESSY_PARAGRAPH != CLEAN_PARAGRAPH
    assert MESSY_CONCLUSION != CLEAN_CONCLUSION
    assert MESSY_CONCLUSION.endswith(". ! ?  \n") and MESSY_CONCLUSION.startswith("\n")
    assert "EITHER" in MESSY_PARAGRAPH and "  the " in MESSY_PARAGRAPH
    assert "’" in CURLY_CONTRACTED


def test_the_messy_fixture_still_produces_a_real_entailment() -> None:
    # And it must not be trivially equal because BOTH sides failed. The clean input entails, so
    # the messy one has to as well.
    assert fingerprint(CLEAN_PARAGRAPH, CLEAN_CONCLUSION)[3] == "ENTAILED"
    assert all(status == "ok" for status in fingerprint(MESSY_PARAGRAPH, MESSY_CONCLUSION)[4])


# ================================================== one normalizer, enforced structurally


def test_prepare_is_idempotent() -> None:
    # Re-preparing an already-prepared sentence must change nothing, or a second pass anywhere in
    # the stack would quietly alter the student's text.
    once = prepare(MESSY_PARAGRAPH)
    assert [prepare(sentence) for sentence in once] == [[sentence] for sentence in once]


def test_no_core_module_normalizes_text_itself() -> None:
    """Only the normalization pipeline may fold or strip text. Everyone else calls `prepare`.

    `ast`, not a grep: the point is to find a module that *does* the work, not one that mentions
    it.

    What counts as normalizing PROSE, and what does not, took two attempts to get right. The
    first version flagged every `lower/upper/strip` call and reported four modules that were all
    innocent: `literal.lstrip("~")` strips a negation marker from a logic symbol, and
    `symbol.upper()` canonicalises a symbol's case. Neither touches a student's sentence.

    So the rule is about the ARGUMENT, not just the method name:

      forbidden   `.lower()`, `.casefold()`  -- folding prose
                  `.strip()` with no argument -- tidying whitespace
      allowed     `.strip("~")` and friends WITH an argument -- removing a known logic marker

    Named exceptions, so adding a fourth is a decision rather than a habit:
      `english.py` owns normalization · `facts.py` lowercases a phrase for its canonical key ·
      `logic.py` upper-cases a propositional SYMBOL, which is its documented job.
    """
    allowed = {"english.py", "facts.py", "logic.py"}
    folding = ("lower", "casefold")
    stripping = ("strip", "lstrip", "rstrip")
    offenders = {}
    for path in sorted(CORE.glob("*.py")):
        if path.name in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = [
            f"{node.func.attr}() at line {node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and (
                node.func.attr in folding
                or (node.func.attr in stripping and not node.args)  # bare strip = tidying prose
            )
        ]
        if found:
            offenders[path.name] = found
    assert not offenders, f"text handling outside the normalizer: {offenders}"


def test_that_check_would_actually_catch_a_second_normalizer() -> None:
    # The guard has to fail on the thing it exists for, and tolerate the four innocent calls it
    # wrongly flagged on the first attempt.
    caught = "text = raw.lower()\nname = other.strip()\n"
    innocent = 'sym = literal.lstrip("~")\nup = symbol.upper()\n'

    def hits(source: str) -> int:
        return sum(
            1
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and (
                node.func.attr in ("lower", "casefold")
                or (node.func.attr in ("strip", "lstrip", "rstrip") and not node.args)
            )
        )

    assert hits(caught) == 2
    assert hits(innocent) == 0


def test_every_known_entry_point_is_covered() -> None:
    """The list above must keep pace with the system.

    Stated as an explicit inventory rather than discovered, because the failure being guarded
    against is someone adding a route and not thinking about normalization at all.
    """
    built = {"session.analyse"}
    pending = {
        "cli prompt": "S3 — covered by test_cli.py driving the same prepare()",
        "api /api/parse": "S4",
        "heldout_eval": "S8",
        "typed formula (M2)": "S6",
    }
    assert set(ENTRY_POINTS) == built, (
        f"ENTRY_POINTS has drifted from the built routes. Still to add: {sorted(pending)}"
    )
