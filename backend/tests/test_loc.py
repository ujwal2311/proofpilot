"""Tests for tools/loc.py -- the budget reporter (docs/HLD.md section 16).

The caps are only as trustworthy as the thing that measures them. A counter that mistook a
string literal for a docstring would quietly inflate the allowance, so it is tested like any
other code.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import loc  # noqa: E402  (needs the path above)

FIXTURE = '''"""Module docstring.

Second line of it.
"""

# a standalone comment
import os


def thing():
    """One-line docstring."""
    banner = """not a docstring -- a multi-line
    string assigned to a name"""
    return banner, os


'''


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(FIXTURE, encoding="utf-8")
    return path


def test_measure_separates_docstrings_from_string_literals(sample: Path) -> None:
    counts = loc.measure(sample)

    # The module docstring is 4 lines (one of which is blank, and must be counted ONCE, as
    # docstring) and the function's is 1. The two-line string bound to a name is NOT a
    # docstring and must count as code -- the distinction a regex cannot make.
    assert counts["total"] == 16
    assert counts["docstring"] == 5
    assert counts["comment"] == 1
    assert counts["blank"] == 5
    assert counts["code"] == 5  # import, def, two string lines, return


def test_measure_counts_every_line_exactly_once(sample: Path) -> None:
    counts = loc.measure(sample)
    assert (
        counts["code"] + counts["docstring"] + counts["comment"] + counts["blank"]
        == (counts["total"])
    )


CORE = ["backend/src/core/*.py"]


def test_main_exits_non_zero_when_a_ceiling_is_exceeded(capsys) -> None:
    assert loc.main({"tiny": {"patterns": CORE, "cap": 0, "ceiling": 0}}) == 1
    assert "OVER CEILING" in capsys.readouterr().out


def test_over_the_cap_but_under_the_ceiling_warns_without_failing(capsys) -> None:
    # The band between the frozen estimate and estimate+10% is a warning the gate report has to
    # justify. A hard stop at the estimate would turn every honest estimate into a lie.
    assert loc.main({"band": {"patterns": CORE, "cap": 1, "ceiling": 10_000}}) == 0
    out = capsys.readouterr().out
    assert "WARN over cap" in out and "OVER CEILING" not in out


def test_main_exits_zero_when_within_cap(capsys) -> None:
    assert loc.main({"roomy": {"patterns": CORE, "cap": 10_000, "ceiling": 11_000}}) == 0
    assert "OVER" not in capsys.readouterr().out


def test_an_uncapped_bucket_is_reported_but_never_fails(capsys) -> None:
    # tools/ is development-only: it never ships, so capping it penalised exactly the work that
    # makes the other caps trustworthy (v2.10 item 4).
    assert loc.main({"free": {"patterns": CORE, "capped": False}}) == 0
    assert "OVER" not in capsys.readouterr().out


def test_real_buckets_are_within_their_ceilings() -> None:
    # The gate check itself, so a breach fails the suite and not only CI.
    assert loc.main() == 0


# ---------------------------------------------------------------- reported totals (v2.11)


def test_a_total_sums_its_members_and_is_printed(capsys) -> None:
    # The condition behind the v2.11 split: a bucket divided for sound design reasons must still
    # show its whole cost, because three small caps read as three small costs.
    buckets = {
        "a": {"patterns": CORE, "cap": 10, "ceiling": 11},
        "b": {"patterns": CORE, "cap": 20, "ceiling": 22},
    }
    assert loc.main(buckets, {"SUM": ["a", "b"]}) == 1  # both over, as expected
    rows = {line.split()[0]: line.split()[1:4] for line in capsys.readouterr().out.splitlines()[1:]}
    assert rows["SUM"][1:] == ["30", "33"], "the total must sum the member caps and ceilings"
    assert int(rows["SUM"][0]) == int(rows["a"][0]) + int(rows["b"][0])


def test_the_core_total_covers_every_core_bucket_and_nothing_else() -> None:
    # The whole point is that no core bucket can hide outside the reported total, so this is
    # checked against the bucket list rather than against a copy of it.
    totals = loc.load_totals()
    assert "CORE TOTAL" in totals, "budgets.toml must report a combined core figure"
    every_core = {name for name in loc.load_buckets() if name.startswith("core")}
    assert set(totals["CORE TOTAL"]) == every_core, (
        f"CORE TOTAL lists {sorted(totals['CORE TOTAL'])}, core buckets are {sorted(every_core)}"
    )


def test_totals_is_not_mistaken_for_a_bucket() -> None:
    # `[totals]` is a TOML table like any other. The first version of load_buckets took every
    # table and crashed on the missing `patterns` key rather than ignoring it.
    assert "totals" not in loc.load_buckets()


def test_the_number_of_capped_buckets_is_frozen() -> None:
    """No more new buckets to absorb an overrun (team condition, 2026-10-12).

    Three buckets were added in two days -- core_m2 at B0, core_session at S2 -- each for a real
    reason, and each one also made the next overrun easier to absorb. That stops here: a further
    overrun is a STOP-and-ask, not a new row in this file. Asserted as a count so adding one
    fails the build and has to be a deliberate, discussed change rather than a quiet commit.
    """
    capped = [name for name, spec in loc.load_buckets().items() if spec.get("capped", True)]
    assert sorted(capped) == [
        "api_cli",
        "core",
        "core_m2",
        "core_session",
        "frontend",
        "scripts",
    ], "a bucket was added or removed; see the v2.11 overrun condition in CLAUDE.md"


def test_an_excluded_file_is_not_counted_twice(capsys) -> None:
    # `core` and `core_m2` share a directory (v2.11), so the M1 bucket excludes the M2 files by
    # name. If `exclude` were ignored, M1 would be measured against an M2 overrun.
    everything = loc.main({"all": {"patterns": CORE, "capped": False}})
    assert everything == 0
    with_all = capsys.readouterr().out

    loc.main({"some": {"patterns": CORE, "exclude": ["backend/src/core/bkt.py"], "capped": False}})
    with_one_dropped = capsys.readouterr().out

    def code_of(text: str) -> int:
        return int(text.splitlines()[1].split()[1])

    assert code_of(with_one_dropped) < code_of(with_all)


def _owners() -> dict[Path, list[str]]:
    owners: dict[Path, list[str]] = {}
    for name, spec in loc.load_buckets().items():
        excluded = {loc.ROOT / p for p in spec.get("exclude", ())}
        for pattern in spec["patterns"]:
            for path in loc.ROOT.glob(pattern):
                if path not in excluded:
                    owners.setdefault(path, []).append(name)
    return owners


# Every shipped or evaluated source tree. `backend/tests` is absent on purpose -- tests are not
# capped, because capping them is an incentive to write fewer.
MEASURED_TREES = (
    "backend/src/**/*.py",
    "scripts/*.py",
    "tools/*.py",
    "frontend/src/**/*.js",
    "frontend/src/**/*.jsx",
    "frontend/src/**/*.css",
)


def test_every_source_file_is_measured_by_exactly_one_bucket() -> None:
    # Two ways a budget stops binding without anyone noticing, and both have happened here:
    #
    #   1. A file matches NO pattern. `backend/src/loader.py` was like this -- the v2.4 change log
    #      placed it in the api+cli bucket, but the pattern listed `cli.py` by name, so the one
    #      module that reads a data file was unmeasured. Found by the F3 fix, not by the budget.
    #   2. A file matches TWO patterns, which is what the v2.11 core/core_m2 exclude list creates
    #      if a new M2 module is added to the pattern list but not to the exclude list.
    #
    # Checked against the trees as they actually are, so adding a source file without budgeting it
    # fails the build.
    owners = _owners()
    for pattern in MEASURED_TREES:
        for path in sorted(loc.ROOT.glob(pattern)):
            if path.name == "__init__.py" and path.stat().st_size == 0:
                continue  # an empty package marker has nothing to budget
            assert owners.get(path), f"{path.relative_to(loc.ROOT)} is in no budget bucket"
            assert len(owners[path]) == 1, (
                f"{path.relative_to(loc.ROOT)} is counted by {owners[path]}"
            )


def test_every_bucket_ceiling_is_the_frozen_estimate_plus_ten_percent() -> None:
    # The rule the student froze (v2.10 item 6). Written as a test so a hand-edited ceiling in
    # budgets.toml cannot quietly become a cap raise.
    #
    # Integer arithmetic, not `ceil(cap * 1.10)`: in binary, 220 * 1.1 is 242.00000000000003, so
    # the float form demands 243 for a bucket whose ceiling is exactly 242. The first draft of
    # this test failed for that reason -- a cap is an exact quantity and is computed exactly.
    for name, spec in loc.load_buckets().items():
        if not spec.get("capped", True):
            continue
        expected = -(-spec["cap"] * 11 // 10)
        assert spec["ceiling"] == expected, f"{name}: ceiling is not cap + 10%"
