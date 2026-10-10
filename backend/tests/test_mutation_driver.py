"""Tests for scripts/mutate.py -- the isolation guarantees (v2.9 A2).

CONTRACT. The driver must satisfy three properties, and all three are asserted here because the
tool failed twice in the same way and a passing suite cannot detect the failure: a SURVIVING
mutant passes the tests by definition, so green says nothing about whether a mutant is still on
disk.

  1. `fingerprint(root)` changes whenever the Python files under `root` change -- in content OR
     in name. This is what lets the driver prove after the fact that nothing moved.
  2. `preflight` refuses a module absent from HEAD, and refuses a dirty tree. Both are tested
     against a throwaway repository: dirtying this one to test the check would be the exact bug
     the check exists to prevent.
  3. `isolated_checkout()` yields a directory outside the repository, and a write inside it
     leaves `backend/src` byte-identical. This is the property the incident violated.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import mutate  # noqa: E402  (needs the path above)

SRC = ROOT / "backend" / "src"


def _repo(path: Path) -> Path:
    """A throwaway git repository with one committed core module."""
    module = path / "backend" / "src" / "core" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("x = 1\n", encoding="utf-8")
    for args in (
        ("init", "-q"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "test"),
        ("add", "-A"),
        ("commit", "-q", "-m", "seed"),
    ):
        subprocess.run(["git", *args], cwd=path, capture_output=True, check=True)
    return module


# ------------------------------------------------------------------------------- fingerprint


def test_fingerprint_notices_a_content_change(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    before = mutate.fingerprint(tmp_path)
    assert mutate.fingerprint(tmp_path) == before, "the hash must be stable, not time-dependent"
    (tmp_path / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert mutate.fingerprint(tmp_path) != before


def test_fingerprint_notices_a_rename(tmp_path: Path) -> None:
    # Paths are hashed as well as bytes. A content-only digest would call a moved file unchanged,
    # which is precisely the drift the post-run check is meant to catch.
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    before = mutate.fingerprint(tmp_path)
    (tmp_path / "a.py").rename(tmp_path / "b.py")
    assert mutate.fingerprint(tmp_path) != before


# ---------------------------------------------------------------------------------- preflight


def test_preflight_accepts_a_clean_repository(tmp_path: Path) -> None:
    _repo(tmp_path)
    mutate.preflight(["sample"], tmp_path)  # must not raise


def test_preflight_refuses_a_module_absent_from_head(tmp_path: Path) -> None:
    # The original incident: `git checkout` silently succeeded on a module git had never seen,
    # so the restore did nothing and the mutant stayed on disk.
    _repo(tmp_path)
    with pytest.raises(SystemExit, match="untracked"):
        mutate.preflight(["never_committed"], tmp_path)


def test_preflight_refuses_a_dirty_tree(tmp_path: Path) -> None:
    module = _repo(tmp_path)
    module.write_text("x = 999\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not clean"):
        mutate.preflight(["sample"], tmp_path)


# --------------------------------------------------------------------------------- isolation


@pytest.mark.skipif(
    os.environ.get(mutate.RUN_FLAG) == "1",
    reason="already inside a mutation run; a nested worktree would test the harness, not the code",
)
def test_a_write_in_the_isolated_checkout_leaves_the_working_tree_untouched() -> None:
    before = mutate.fingerprint(SRC)
    with mutate.isolated_checkout() as tree:
        assert ROOT not in tree.parents and tree != ROOT, "the checkout must be outside the repo"
        target = tree / "backend" / "src" / "core" / "search.py"
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\nMUTANT = True\n", encoding="utf-8")
        assert target.read_text(encoding="utf-8") != original, "the copy must be writable"
        assert mutate.fingerprint(SRC) == before, "the real source changed -- isolation failed"
    assert mutate.fingerprint(SRC) == before
    assert not tree.exists(), "the worktree must be removed afterwards"
