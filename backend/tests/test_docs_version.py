"""Docs must not drift from the things they cite -- the HLD version, and the line budgets.

Version drift is silent and embarrassing: a reading guide pointing at a superseded design reads
as carelessness in a viva. The HLD itself is excluded from the version check -- its change log
cites old versions on purpose.

The budget check exists because the caps were duplicated across three HLD tables for six
revisions and all three drifted: §2, §13.4 and §17.12 were still printing a 975-line core cap
while CI enforced 650. `budgets.toml` is now the single source (v2.10 item 5), and a cap number
written into prose fails the build rather than waiting to be noticed.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERRING_DOCS = ("CLAUDE.md", "README.md", "docs/READING_GUIDE.md")
VERSION_TOKEN = re.compile(r"v(\d+\.\d+)")

sys.path.insert(0, str(ROOT / "tools"))

# Every doc that a reader might mistake for authoritative. HLD_REVIEW.md is excluded: it is a
# dated historical review and quoting the numbers of its day is the point of it.
BUDGET_FREE_DOCS = ("CLAUDE.md", "README.md", "docs/HLD.md", "docs/READING_GUIDE.md")


def test_docs_reference_current_hld_version() -> None:
    header = (ROOT / "docs" / "HLD.md").read_text(encoding="utf-8").splitlines()[0]
    current = re.search(r"v(\d+\.\d+)", header).group(1)

    for name in REFERRING_DOCS:
        path = ROOT / name
        stale = set(VERSION_TOKEN.findall(path.read_text(encoding="utf-8"))) - {current}
        assert not stale, f"{name} references v{sorted(stale)}; docs/HLD.md declares v{current}"


# A narrow, visible opt-out. A cap must never be RESTATED in prose, because prose drifts -- but a
# change-log entry recording what was MEASURED on a given date is a historical record, and the
# numbers are the whole point of it (the same reason HLD_REVIEW.md is excluded outright). The
# marker is a fenced block rather than a section exemption, so a live cap still cannot be quoted
# anywhere in §16 by accident, and every exemption is greppable.
MEASURED_OPEN = "<!-- measured-numbers:"
MEASURED_CLOSE = "<!-- /measured-numbers -->"


def _without_measured_blocks(text: str) -> str:
    """The document with every fenced measurement block blanked out, line count preserved."""
    kept, inside = [], False
    for line in text.splitlines():
        if line.strip().startswith(MEASURED_OPEN):
            inside = True
        kept.append("" if inside else line)
        if line.strip() == MEASURED_CLOSE:
            inside = False
    assert not inside, "an unclosed measured-numbers block would exempt the rest of the file"
    return "\n".join(kept)


# A textual guard cannot tell a two-digit cap from an ordinary number. The `core_session` cap of
# 85 collided with three unrelated figures in docs/HLD.md alone -- "~85x margin" in the latency
# table, "~70-85 lines" in a v2.2 decision row, and a test count -- and fencing those would mean
# exempting prose that is not a measurement at all, which is how an exemption becomes a loophole.
#
# So the guard covers caps of 100 or more. The LIMITATION is stated rather than hidden: a
# two-digit cap is not protected by this check. It is the smallest bucket, and the cost of the
# alternative -- a guard that cries wolf until someone disables it -- is worse than the gap.
GUARDABLE = 100


def _cap_numbers() -> set[int]:
    budgets = tomllib.loads((ROOT / "budgets.toml").read_text(encoding="utf-8"))
    return {
        value
        for table in budgets.values()
        if isinstance(table, dict)
        for key, value in table.items()
        if key in ("cap", "ceiling") and value >= GUARDABLE
    }


def test_no_doc_restates_a_cap_number() -> None:
    numbers = _cap_numbers()
    assert numbers, "budgets.toml declared no caps -- the guard would pass vacuously"

    for name in BUDGET_FREE_DOCS:
        text = _without_measured_blocks((ROOT / name).read_text(encoding="utf-8"))
        for number in sorted(numbers):
            # Word-bounded so that 805 does not match 1805, and so a year or a line reference
            # cannot be mistaken for a cap.
            found = re.search(rf"(?<![\d,.]){number}(?![\d,.])", text)
            assert not found, (
                f"{name} writes the cap number {number}. budgets.toml is the single source "
                f"(v2.10 item 5) -- reference the file, never restate its numbers."
            )


def test_the_budget_guard_would_actually_fail(tmp_path: Path) -> None:
    # A guard nobody has seen fail is a guard nobody should trust. Proves the regex matches a
    # restated cap and tolerates a number that merely contains one.
    cap = tomllib.loads((ROOT / "budgets.toml").read_text(encoding="utf-8"))["core"]["cap"]
    assert re.search(rf"(?<![\d,.]){cap}(?![\d,.])", f"core is capped at {cap} lines")
    assert not re.search(rf"(?<![\d,.]){cap}(?![\d,.])", f"see line 1{cap}0")
    # And the documented gap is real, not accidental: the small caps are knowingly out of scope.
    unguarded = {
        name
        for name, spec in tomllib.loads((ROOT / "budgets.toml").read_text(encoding="utf-8")).items()
        if isinstance(spec, dict) and spec.get("cap", GUARDABLE) < GUARDABLE
    }
    assert unguarded == {"core_session"}, f"a new small-cap bucket is unguarded: {unguarded}"


def test_the_measured_number_exemption_stays_narrow() -> None:
    """The opt-out must not grow into a way of putting caps back into prose.

    Each block has to name what was measured and when, and there must be few of them. A fenced
    exemption is only safe while it is rare enough that a reader notices one.
    """
    import re

    found = []
    for name in BUDGET_FREE_DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
        for label in re.findall(rf"{re.escape(MEASURED_OPEN)}(.*?)-->", text):
            assert re.search(r"\d{4}-\d{2}-\d{2}", label), (
                f"{name}: measured-numbers block {label!r} must carry the date it was measured"
            )
            found.append(f"{name}:{label.strip()}")
    assert len(found) <= 3, (
        f"too many measurement exemptions, the guard is being worked around: {found}"
    )
    assert found, "the exemption is unused -- delete the mechanism rather than leaving it armed"


def test_the_guard_still_fires_outside_a_measured_block() -> None:
    # The exemption must be the only hole. Proves a cap quoted in ordinary prose is still caught
    # even in a document that legitimately contains one measurement block.
    cap = tomllib.loads((ROOT / "budgets.toml").read_text(encoding="utf-8"))["core"]["cap"]
    doc = f"""# Doc
{MEASURED_OPEN} S2, 2026-10-12 -->
core measured {cap} here, which is a record
{MEASURED_CLOSE}
and the cap is {cap} lines, a restatement
"""
    stripped = _without_measured_blocks(doc)
    assert "record" not in stripped
    assert re.search(rf"(?<![\d,.]){cap}(?![\d,.])", stripped), "the live restatement must survive"
