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

The target file is restored with `git checkout` in a finally block, so a hanging mutant cannot
leave the tree modified -- which is exactly what happened once before this driver existed.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = json.loads((ROOT / "data" / "mutants.json").read_text(encoding="utf-8"))
TIMEOUT_SECONDS = 90


def run_one(target: Path, mutant: dict) -> tuple[str, str]:
    original = target.read_text(encoding="utf-8")
    if mutant["find"] not in original:
        return "not-applied", "anchor text absent -- retired by a refactor"
    target.write_text(original.replace(mutant["find"], mutant["replace"], 1), encoding="utf-8")
    try:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-x"],
            cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
        )
        summary = next(
            (ln for ln in reversed(done.stdout.splitlines()) if "passed" in ln or "failed" in ln),
            f"exit {done.returncode}",
        )
        return ("caught" if done.returncode else "SURVIVED"), summary
    except subprocess.TimeoutExpired:
        return "caught", f"hung past {TIMEOUT_SECONDS}s -- non-terminating, counted as caught"
    finally:
        subprocess.run(["git", "checkout", "--", str(target)], cwd=ROOT, check=True)


def main(only: str | None = None) -> int:
    caught = survived = retired = 0
    for module, mutants in sorted(MUTANTS.items()):
        if only and module != only:
            continue
        target = ROOT / "backend" / "src" / "core" / f"{module}.py"
        print(f"\n== {module}.py ==")
        for mutant in mutants:
            verdict, detail = run_one(target, mutant)
            caught += verdict == "caught"
            survived += verdict == "SURVIVED"
            retired += verdict == "not-applied"
            print(f"{mutant['id']:6} {mutant['desc']:48} {verdict:11} {detail}")
    scored = caught + survived
    print(f"\nscore: {caught}/{scored} caught" + (f", {retired} retired" if retired else ""))
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
