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


def test_a_breached_ceiling_is_reported_and_blocks_only_in_strict_mode(capsys) -> None:
    # Caps REPORT during the sprint; `--strict` restores blocking (see the sprint rule below).
    tiny = {"tiny": {"patterns": CORE, "cap": 0, "ceiling": 0}}
    assert loc.main(tiny) == 0
    assert "OVER CEILING" in capsys.readouterr().out
    assert loc.main(tiny, strict=True) == 1


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


def test_the_real_bucket_table_is_reported(capsys) -> None:
    """Caps REPORT; they no longer block (sprint rule, 2026-10-12, expires at progress-v1).

    Five budget stops in one sprint were all estimation error rather than bloat -- the §7
    pipeline, the data loader, the shared edge, `state_of` -- and a cap on a bucket was only ever
    a proxy for "both members can explain every module". The blocking gates now measure that
    directly: `ruff C901` and the per-function length gate below.

    What this test still guarantees is that the table is PRODUCED, with a row per bucket, so the
    numbers appear in every block report and a drift is visible even though it is not fatal.
    """
    assert loc.main() == 0, "caps must not block while the sprint rule is in force"
    rows = capsys.readouterr().out.splitlines()
    labelled = {spec.get("label", name) for name, spec in loc.load_buckets().items()}
    printed = {line.split()[0] for line in rows[1:] if line.strip()}
    assert labelled <= {p for row in rows[1:] for p in [row[:15].strip()]}, (
        f"a bucket is missing from the table: {labelled - printed}"
    )


def test_strict_mode_still_blocks_so_the_capability_is_not_lost() -> None:
    # The sprint rule expires at the tag. `--strict` is how the pre-sprint behaviour comes back,
    # and a switch nobody exercises is a switch that has quietly rotted by then.
    tiny = {"tiny": {"patterns": CORE, "cap": 0, "ceiling": 0}}
    assert loc.main(tiny, strict=True) == 1
    assert loc.main(tiny, strict=False) == 0


# ------------------------------------------------- the blocking explainability gates (sprint)


def test_no_function_exceeds_the_length_gate() -> None:
    # BLOCKING. The replacement for the bucket caps: a function longer than a screen cannot be
    # explained in a viva from the screen, which is what the caps were a proxy for.
    assert loc.check_functions() == 0


def test_the_length_gate_would_actually_fail() -> None:
    # A guard nobody has seen fail is a guard nobody should trust. Run at a limit of 1, every
    # function in the repo breaches, so a non-zero result proves the gate is wired to something.
    assert loc.check_functions(limit=1) == 1


def test_the_length_gate_measures_code_not_prose() -> None:
    # It must count what the buckets count. A docstring is required by rule 9 and WHY-comments
    # are the point of the codebase; a function of two statements wrapped in eighty lines of
    # explanation must measure 2, or the gate would punish exactly the work it exists to reward.
    source = 'def wordy():\n    """A deliberately long explanation."""\n'
    source += "".join(f"    # comment {n}\n" for n in range(80))
    source += "    return 1\n"

    label = loc._labels(source)
    lines = source.splitlines()
    code = sum(
        1
        for row in range(len(lines))
        if not label[row] and lines[row].strip() and not lines[row].strip().startswith("#")
    )
    assert code == 2, f"a docstring and 80 comments were charged as code: {code}"


def test_the_complexity_gate_is_configured_and_can_fail(tmp_path: Path) -> None:
    """`ruff C901` at max-complexity 10, the other blocking explainability gate.

    Asserted two ways: that it is selected in `pyproject.toml` with the threshold, and that ruff
    actually reports a breach. A gate that is configured but unreachable is no gate.
    """
    import subprocess
    import sys
    import tomllib

    config = tomllib.loads((loc.ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lint = config["tool"]["ruff"]["lint"]
    assert "C901" in lint["select"], "C901 is not selected; the complexity gate is off"
    assert lint["mccabe"]["max-complexity"] == 10

    # A function with twelve branches. Checked through the real `ruff` the CI job runs, not a
    # reimplementation of mccabe.
    branches = "".join(f"    if n == {n}:\n        return {n}\n" for n in range(12))
    sample = tmp_path / "complex_sample.py"
    sample.write_text(f"def tangled(n):\n{branches}    return None\n", encoding="utf-8")
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "C901",
            "--isolated",
            "--config",
            "lint.mccabe.max-complexity = 10",
            str(sample),
        ],
        capture_output=True,
        cwd=loc.ROOT,
    )
    assert done.returncode == 1, "ruff did not flag a 12-branch function"
    assert b"C901" in done.stdout


def test_the_real_tree_passes_the_complexity_gate() -> None:
    # The gate itself, so a breach fails the suite and not only CI. It found two functions the
    # day it was switched on -- the grammar's `parse_sentence` at 18 and the CLI's command chain
    # at 11 -- and both were fixed by extraction.
    import subprocess
    import sys

    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "C901",
            "backend/src",
            "tools",
            "scripts",
        ],
        capture_output=True,
        cwd=loc.ROOT,
    )
    assert done.returncode == 0, done.stdout.decode("utf-8", "replace")


def test_the_allowlist_is_printed_and_currently_empty(capsys) -> None:
    """An exemption nobody sees is an exemption nobody revisits.

    Empty at the time the gate was switched on: the longest function was 48 lines, and the two
    complexity breaches it found were fixed by extraction rather than excused.
    """
    import tomllib

    allowed = tomllib.loads((loc.ROOT / "budgets.toml").read_text(encoding="utf-8"))
    assert allowed.get("long_functions") == {}, (
        f"the length-gate allowlist is no longer empty: {allowed['long_functions']}. "
        f"Each entry needs a one-line reason and should be a last resort."
    )
    loc.check_functions()
    assert "function length gate" in capsys.readouterr().out


# ---------------------------------------------------------------- reported totals (v2.11)


def test_a_total_sums_its_members_and_is_printed(capsys) -> None:
    # The condition behind the v2.11 split: a bucket divided for sound design reasons must still
    # show its whole cost, because three small caps read as three small costs.
    buckets = {
        "a": {"patterns": CORE, "cap": 10, "ceiling": 11},
        "b": {"patterns": CORE, "cap": 20, "ceiling": 22},
    }
    assert loc.main(buckets, {"SUM": ["a", "b"]}) == 0  # both over, but caps only report now
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
