"""No doc or workflow may point at a file that does not exist.

A real stale reference got through: after S3 moved the loader to `app/data.py`, the HLD still
pointed at `backend/src/loader.py` in three places, and only a hand-written audit found it. A
reader sent to a deleted file is worse than one sent nowhere, and in a viva it reads as a document
nobody maintains. The CI workflow is scanned for the same reason — a workflow naming a script that
has moved fails the build at the worst possible moment.

EVERYTHING IS NORMALISED TO ONE FORM before any comparison: repo-root-relative POSIX. Scanned
file names, extracted mentions and the exemption lists are all in that form, so `docs\\HLD.md` on
a Windows runner and `docs/HLD.md` on Ubuntu are the same string. An earlier version compared
absolute paths against relative ones and its whole-file exemption silently never matched.

THE TWO EXEMPTION RULES, stated here rather than left to be inferred:

  1. A **HISTORICAL BLOCK** is exempt. Blocks are fenced regions, parsed as line ranges, so
     markdown wrapping cannot matter:

         <!-- historical: <label with a date> -->  …  <!-- /historical -->
         <!-- measured-numbers: <label with a date> -->  …  <!-- /measured-numbers -->

     The HLD's whole change log (§16) is fenced this way. Every entry in it is dated and describes
     the repository as it stood when it was written, so a file it names may since have moved;
     rewriting those names would falsify the record. `AI_USAGE_LOG.md` and `docs/HLD_REVIEW.md`
     are exempt as whole files for the same reason — the first is append-only by CLAUDE.md rule 5,
     the second is a dated v1 review.

     There is deliberately NO line-level marker. The first version had one and reported a
     reference that its own annotation, two wrapped lines above, had already explained.

  2. A **PLANNED** file is exempt until its block builds it. The list is explicit, each entry
     names the block, and `test_the_planned_list_shrinks` fails once an entry exists — so the
     allowlist cannot outlive the work and start hiding real staleness.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    """THE one form: repo-root-relative POSIX. Everything is compared in it."""
    return path.resolve().relative_to(ROOT).as_posix()


SCANNED = tuple(
    rel(path)
    for pattern in ("*.md", "docs/**/*.md", ".github/workflows/*.yml")
    for path in sorted(ROOT.glob(pattern))
)

# Whole-file exemptions (rule 1).
DATED_RECORDS = ("AI_USAGE_LOG.md", "docs/HLD_REVIEW.md")

# Fenced historical regions (rule 1). Both marker pairs count: `measured-numbers` already existed
# for the budget guard, and re-using it here avoids a second fence around the same text.
FENCES = (
    ("<!-- historical:", "<!-- /historical -->"),
    ("<!-- measured-numbers:", "<!-- /measured-numbers -->"),
)

# Rule 2 -- shrinks as the sprint lands each block.
PLANNED = {
    "data/heldout_paragraphs.json": "S8 -- written by the team, never by Claude",
    "docs/misconceptions.md": "S10",
    "frontend/src/TranslateStep.jsx": "deferred M2 scope (HLD v2.12 change log), not yet built",
    "backend/src/core/unify.py": "HLD v2.14 S18.4 -- FOL sprint Phase 4",
    "backend/src/core/fol_resolve.py": "HLD v2.14 S18.5 -- FOL sprint Phase 5",
    "backend/src/core/fol_english.py": "HLD v2.14 S18.2 -- FOL sprint Phase 6",
    "backend/src/core/fol_search.py": "HLD v2.14 S18.6 -- FOL sprint Phase 7",
}

# Docs write a module path relative to the package as often as to the repo root --
# "`core/tutor.py`", "`app/data.py`" -- so a mention is tried under each of these prefixes and
# normalised to whichever one resolves.
PREFIXES = ("", "backend/", "backend/src/")

# Paths are written in backticks. Matched on a trailing extension, so prose about a directory
# ("`core/`") is not mistaken for a file and a bare word in backticks ("`State`") is ignored.
MENTION = re.compile(r"`([A-Za-z0-9_./\\-]+\.(?:py|json|yaml|yml|toml|md|jsx?|css|cfg|ini|csv))`")

# Non-vacuity floors. A guard that silently scans nothing passes forever.
MIN_DOCS = 6
MIN_MENTIONS = 60


def _live_text(text: str) -> str:
    """The document with every fenced historical region blanked out, line count preserved."""
    kept: list[str] = []
    closing: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if closing is None:
            opened = next((c for o, c in FENCES if stripped.startswith(o)), None)
            if opened is not None:
                closing = opened
                kept.append("")
                continue
            kept.append(line)
        else:
            kept.append("")
            if stripped == closing:
                closing = None
    assert closing is None, "unclosed historical fence; it would exempt the rest of the file"
    return "\n".join(kept)


def _mentions(text: str) -> list[str]:
    """Every path mentioned in live prose, normalised to repo-root-relative POSIX."""
    found = []
    for raw in MENTION.findall(_live_text(text)):
        quoted = raw.replace("\\", "/")
        # A bare filename is ambiguous ("`config.py`" means core's), so only paths with a
        # directory are resolved -- those are the ones a reader actually follows.
        if "/" not in quoted:
            continue
        hit = next(
            ((ROOT / (p + quoted)) for p in PREFIXES if (ROOT / (p + quoted)).exists()), None
        )
        found.append(rel(hit) if hit else quoted)
    return found


def _is_known(mention: str) -> bool:
    """Does this mention resolve, or is it a planned file?

    PLANNED is checked under the same prefixes as the filesystem. A path that does not exist
    cannot be normalised by resolving it, so a doc writing "`api/schemas.py`" and a PLANNED entry
    of "backend/src/api/schemas.py" are the same file and must compare equal.
    """
    return any(
        (ROOT / (prefix + mention)).exists() or (prefix + mention) in PLANNED for prefix in PREFIXES
    )


@pytest.mark.parametrize("name", [n for n in SCANNED if n not in DATED_RECORDS])
def test_no_doc_or_workflow_points_at_a_file_that_does_not_exist(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    gone = sorted({m for m in _mentions(text) if not _is_known(m)})
    assert not gone, f"{name} points at files that do not exist: {gone}"


def test_the_planned_list_shrinks() -> None:
    """An allowlist that outlives the work is an allowlist that hides the next stale reference."""
    built = {q: block for q, block in PLANNED.items() if (ROOT / q).exists()}
    assert not built, f"PLANNED still lists files that now exist -- remove them: {built}"


def test_the_mutation_targets_all_exist() -> None:
    # `tools/mutate.py` maps a block name to backend/src/core/<name>.py, so a block naming a
    # renamed module reports "not applied" -- which looks like a passing run with fewer mutants.
    blocks = json.loads((ROOT / "data" / "mutants.json").read_text(encoding="utf-8"))
    for block in blocks:
        target = ROOT / "backend" / "src" / "core" / f"{block}.py"
        assert target.is_file(), f"mutant block {block!r} targets a module that does not exist"


def test_the_guard_is_not_vacuous_and_reports_its_coverage(capsys) -> None:
    """(c) in the brief: prove it is actually looking at something.

    Printed as well as asserted, so the numbers appear in the CI log and a sudden drop is visible
    rather than merely non-failing.
    """
    checked = {name: _mentions((ROOT / name).read_text(encoding="utf-8")) for name in SCANNED}
    live = {n: m for n, m in checked.items() if n not in DATED_RECORDS}
    total = sum(len(m) for m in live.values())
    with capsys.disabled():
        print(f"\n  dead-reference guard: {len(live)} docs scanned, {total} path mentions checked")
    assert len(live) >= MIN_DOCS, f"only {len(live)} docs scanned"
    assert total >= MIN_MENTIONS, f"only {total} mentions checked"


def test_both_directions_of_the_historical_exemption() -> None:
    """(a) a fake path in normal prose FAILS; (b) the same path inside a block PASSES."""
    fake = "backend/src/core/does_not_exist.py"

    plain = f"The loader lives in `{fake}` today.\n"
    assert [m for m in _mentions(plain) if not _is_known(m)] == [fake]

    fenced = (
        f"<!-- historical: S1, 2026-10-12 -->\n\nIt was `{fake}` then.\n\n<!-- /historical -->\n"
    )
    assert [m for m in _mentions(fenced) if not _is_known(m)] == []

    measured = f"<!-- measured-numbers: S3, 2026-10-12 -->\n`{fake}`\n<!-- /measured-numbers -->\n"
    assert [m for m in _mentions(measured) if not _is_known(m)] == []

    # The fence must close. An unclosed one would exempt everything after it.
    with pytest.raises(AssertionError, match="unclosed"):
        _live_text(f"<!-- historical: no close -->\n`{fake}`\n")

    # And a path AFTER a closed fence is live again.
    after = f"<!-- historical: x, 2026-10-12 -->\n<!-- /historical -->\nnow `{fake}` is live\n"
    assert [m for m in _mentions(after) if not _is_known(m)] == [fake]


def test_every_historical_fence_carries_a_date() -> None:
    # An exemption without a date is not a historical record, it is a way of silencing the guard.
    for name in SCANNED:
        text = (ROOT / name).read_text(encoding="utf-8")
        for opening, _ in FENCES:
            for label in re.findall(rf"{re.escape(opening)}(.*?)-->", text, re.S):
                assert re.search(r"\d{4}-\d{2}-\d{2}", label), (
                    f"{name}: historical fence {label.strip()[:60]!r} carries no date"
                )


def test_windows_and_posix_spellings_normalise_to_the_same_thing() -> None:
    # The windows-2025 CI jobs read the same docs. A mention written with backslashes must resolve
    # identically, and `rel()` must produce forward slashes on both platforms.
    assert _mentions("see `backend\\src\\cli.py`") == ["backend/src/cli.py"]
    assert _mentions("see `backend/src/cli.py`") == ["backend/src/cli.py"]
    assert "\\" not in rel(ROOT / "backend" / "src" / "cli.py")
