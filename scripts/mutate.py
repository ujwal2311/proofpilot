"""Mutation testing driver: regenerates every number in docs/experiments/mutation_log.md.

    python scripts/mutate.py            # every module
    python scripts/mutate.py cnf        # one module

A passing suite proves nothing on its own, so each mutant injects one deliberate defect and the
suite is re-run. A mutant that survives means the tests cannot see that defect.

CONVENTIONS, because they affect the score:
  * A mutant is CAUGHT when pytest exits non-zero.
  * A TIMEOUT counts as caught. A non-terminating conversion is a defect the suite surfaced, and
    treating it as a survivor would reward code that hangs over code that fails.
  * NOT-APPLIED means the anchor text no longer exists. Mutants are tied to the code as written,
    so refactoring retires them; they are reported, never silently skipped, and never scored.

ISOLATION (v2.9 A2). Two earlier designs damaged the working tree: `git checkout` silently failed
on a module that was not yet committed, and restore-from-memory still writes to the real file, so
a crash between write and restore leaves a mutant on disk. A SURVIVING mutant passes the tests by
definition, so a green suite is no evidence the files are clean. The fix is structural rather than
another careful restore:

  1. mutations are applied only inside a detached `git worktree` at HEAD -- a separate directory,
     so the real files are never opened for writing at all;
  2. the run refuses to start if the working tree is dirty or a target file is untracked, because
     then HEAD is not what the student is testing;
  3. `backend/src` is fingerprinted before and after, and a difference aborts the run.

That it is a worktree, not a copy, also means mutants are always applied to COMMITTED content: a
stale editor buffer cannot leak into a published score.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = json.loads((ROOT / "data" / "mutants.json").read_text(encoding="utf-8"))
TIMEOUT_SECONDS = 90

# Set in the child pytest environment so the driver's own self-check can tell it is running inside
# a mutation run and skip creating a nested worktree.
RUN_FLAG = "PROOFPILOT_MUTATION_RUN"


def git(*args: str, cwd: Path = ROOT) -> str:
    """Run git and return stdout. Bytes are decoded here because core files hold non-ASCII."""
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)
    return done.stdout.decode("utf-8")


def fingerprint(root: Path) -> str:
    """One hash over every .py file under `root`, path included.

    Paths are hashed as well as contents so that a rename or a deletion changes the digest; a
    content-only hash would call a moved file unchanged.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def preflight(modules: list[str], root: Path = ROOT) -> None:
    """Refuse to start unless HEAD is exactly what is on disk. Raises SystemExit.

    `root` is a parameter so the refusals can be tested against a throwaway repository; testing
    them by deliberately dirtying this one would be the bug the check exists to prevent.
    """
    for module in modules:
        rel = f"backend/src/core/{module}.py"
        if git("ls-files", "--", rel, cwd=root).strip() != rel:
            raise SystemExit(f"refusing to run: {rel} is untracked, so it is absent from HEAD")
    dirty = git("status", "--porcelain", cwd=root).strip()
    if dirty:
        raise SystemExit(
            f"refusing to run: working tree is not clean, so HEAD is not what you\n"
            f"would be testing:\n{dirty}"
        )


@contextmanager
def isolated_checkout():
    """A detached worktree at HEAD, removed afterwards. The only place a mutation is written."""
    parent = Path(tempfile.mkdtemp(prefix="proofpilot-mutate-"))
    tree = parent / "head"
    git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
    try:
        yield tree
    finally:
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(parent, ignore_errors=True)


def run_one(tree: Path, target: Path, mutant: dict) -> tuple[str, str]:
    original = target.read_text(encoding="utf-8")
    if mutant["find"] not in original:
        return "not-applied", "anchor text absent -- retired by a refactor"
    target.write_text(original.replace(mutant["find"], mutant["replace"], 1), encoding="utf-8")
    try:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-x"],
            cwd=tree,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, RUN_FLAG: "1"},
        )
        summary = next(
            (ln for ln in reversed(done.stdout.splitlines()) if "passed" in ln or "failed" in ln),
            f"exit {done.returncode}",
        )
        return ("caught" if done.returncode else "SURVIVED"), summary
    except subprocess.TimeoutExpired:
        return "caught", f"hung past {TIMEOUT_SECONDS}s -- non-terminating, counted as caught"
    finally:
        # Still restored, even though the file is a throwaway: it keeps each mutant independent
        # of the one before it, which is the whole point of scoring them separately.
        target.write_text(original, encoding="utf-8", newline="")


def main(only: str | None = None) -> int:
    modules = [name for name in sorted(MUTANTS) if only is None or name == only]
    if not modules:
        raise SystemExit(f"no mutants defined for {only!r}; known: {', '.join(sorted(MUTANTS))}")
    preflight(modules)
    src = ROOT / "backend" / "src"
    before = fingerprint(src)

    caught = survived = retired = 0
    with isolated_checkout() as tree:
        print(f"mutating inside {tree} -- {src} is not written to")
        for module in modules:
            target = tree / "backend" / "src" / "core" / f"{module}.py"
            print(f"\n== {module}.py ==")
            for mutant in MUTANTS[module]:
                verdict, detail = run_one(tree, target, mutant)
                caught += verdict == "caught"
                survived += verdict == "SURVIVED"
                retired += verdict == "not-applied"
                print(f"{mutant['id']:6} {mutant['desc']:48} {verdict:11} {detail}")

    if fingerprint(src) != before:
        raise SystemExit("ABORT: backend/src changed during the run -- isolation failed")
    scored = caught + survived
    print(f"\nsource fingerprint unchanged: {before[:12]}")
    print(f"score: {caught}/{scored} caught" + (f", {retired} retired" if retired else ""))
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
