"""Tests for scripts/loc.py -- the budget reporter (docs/HLD.md v2.5 section 16).

The caps are only as trustworthy as the thing that measures them. A counter that mistook a
string literal for a docstring would quietly inflate the allowance, so it is tested like any
other code.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

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


def test_main_exits_non_zero_when_a_cap_is_exceeded(capsys) -> None:
    assert loc.main({"tiny": (["backend/src/core/*.py"], 0)}) == 1
    assert "OVER" in capsys.readouterr().out


def test_main_exits_zero_when_within_cap(capsys) -> None:
    assert loc.main({"roomy": (["backend/src/core/*.py"], 10_000)}) == 0
    assert "OVER" not in capsys.readouterr().out


def test_real_buckets_are_within_their_caps() -> None:
    # The gate check itself, so a breach fails the suite and not only CI.
    assert loc.main() == 0
