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


def test_no_doc_restates_a_cap_number() -> None:
    budgets = tomllib.loads((ROOT / "budgets.toml").read_text(encoding="utf-8"))
    numbers = {
        value
        for table in budgets.values()
        if isinstance(table, dict)
        for key, value in table.items()
        if key in ("cap", "ceiling")
    }
    assert numbers, "budgets.toml declared no caps -- the guard would pass vacuously"

    for name in BUDGET_FREE_DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
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
