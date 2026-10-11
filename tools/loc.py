"""Report code lines per bucket, and enforce the per-function length gate.

Code lines only: docstrings and WHY-comments are required by CLAUDE.md rule 9 and improve
explainability, so penalising them would be backwards. Docstrings are found with `tokenize`, never
regex -- a regex cannot tell a docstring from a string literal that merely starts a line.

**BUCKET CAPS ARE REPORTED, NOT BLOCKING** (sprint rule, 2026-10-12, expires at `progress-v1`).
Five budget stops in one sprint were all caused by estimates that had missed real code -- the
§7 pipeline, the data loader, the shared edge, `state_of` -- rather than by bloat. The caps were
only ever a proxy for "both members can explain every module", so they were replaced by gates that
measure that directly, and the table is printed at every block report so the totals stay visible.

**THE BLOCKING GATES** are:

  * `ruff C901` with `max-complexity = 10` (configured in `pyproject.toml`);
  * **every function at most `MAX_FUNCTION_LINES` code lines** -- `--functions`, below.

A function may be allowlisted in `budgets.toml` under `[long_functions]` with a one-line reason.
The allowlist is PRINTED whenever the gate runs, so an exemption is visible in the CI log rather
than buried in a config file.

`--strict` restores the pre-sprint behaviour of failing on a ceiling, so the capability is not
lost while the sprint rule is in force.
"""

import ast
import sys
import tokenize
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = ROOT / "budgets.toml"

# A function longer than this cannot be explained in a viva from the screen, which is the thing
# the old bucket caps were a proxy for. 60 is roughly a screenful; the longest function in the
# repo when the gate was switched on was 48, so it was chosen to be met, not to force churn.
MAX_FUNCTION_LINES = 60
# Trees the gate covers: everything shipped or run. Tests are excluded -- a long, linear test is
# not a comprehension problem, and capping tests is an incentive to write fewer.
GATED = ("backend/src/**/*.py", "tools/*.py", "scripts/*.py")


def load_buckets(path: Path = BUDGETS) -> dict[str, dict]:
    """Bucket definitions from budgets.toml, in declaration order.

    A table only counts as a bucket if it declares `patterns`; `[totals]` is a table too, and
    treating it as a bucket crashed on the missing key rather than being ignored.
    """
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        name: table
        for name, table in config.items()
        if isinstance(table, dict) and "patterns" in table
    }


def load_totals(path: Path = BUDGETS) -> dict[str, list[str]]:
    """Reported sums: label -> the buckets it adds up.

    They exist so that splitting a bucket can never hide a total. `core` is three buckets for
    sound design reasons, and three small caps read as three small costs unless the whole tree is
    printed next to them (team condition, 2026-10-12).
    """
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    return config.get("totals", {})


def _labels(text: str) -> list[str]:
    """Mark the rows of a Python source that belong to a docstring.

    Shared by `measure` and `function_lengths` so a bucket and a function can never disagree
    about what counts as a code line.
    """
    label = [""] * len(text.splitlines())
    for token in tokenize.generate_tokens(iter(lines_with_ends(text)).__next__):
        if token.type == tokenize.STRING and token.line.strip().startswith(('"""', "'''")):
            for row in range(token.start[0] - 1, token.end[0]):
                label[row] = "docstring"
    return label


def measure(path: Path) -> dict[str, int]:
    """Classify every line into exactly ONE bucket.

    Counting the buckets independently double-counts a blank line inside a docstring, which
    subtracts it twice and silently inflates the code allowance. Each line is labelled once,
    docstring first, so the four buckets always sum to the total.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    # tokenize is Python-only; JS/CSS comments are handled by the prefix test below.
    label = _labels(text) if path.suffix == ".py" else [""] * len(lines)

    for row, line in enumerate(lines):
        if label[row]:
            continue
        label[row] = (
            "comment"
            if line.strip().startswith(("#", "//"))
            else "blank"
            if not line.strip()
            else "code"
        )

    counts = {kind: label.count(kind) for kind in ("code", "docstring", "comment", "blank")}
    counts["total"] = len(lines)
    return counts


def lines_with_ends(text: str) -> list[str]:
    return [line + "\n" for line in text.splitlines()] + [""]


def function_lengths(roots: tuple[str, ...] = GATED) -> list[tuple[int, str, str]]:
    """(code lines, where, name) for every function in the gated trees, longest first.

    Code lines by the same `tokenize` labelling the buckets use, so a function and a bucket cannot
    disagree about what a line is. Nested functions are reported in their own right AND counted
    inside their parent: a long closure makes its enclosing function hard to read too.
    """
    found = []
    for pattern in roots:
        for path in sorted(ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8")
            label = _labels(text)
            lines = text.splitlines()
            for node in ast.walk(ast.parse(text)):
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                count = sum(
                    1
                    for row in range(node.lineno - 1, node.end_lineno)
                    if not label[row]
                    and lines[row].strip()
                    and not lines[row].strip().startswith("#")
                )
                found.append(
                    (count, f"{path.relative_to(ROOT).as_posix()}:{node.lineno}", node.name)
                )
    return sorted(found, reverse=True)


def check_functions(limit: int = MAX_FUNCTION_LINES) -> int:
    """The BLOCKING length gate. Prints the allowlist, then returns 1 on any unexcused breach."""
    allowed = tomllib.loads(BUDGETS.read_text(encoding="utf-8")).get("long_functions", {})
    lengths = function_lengths()
    over = [(n, where, name) for n, where, name in lengths if n > limit and name not in allowed]

    longest = lengths[0] if lengths else (0, "-", "-")
    print(
        f"\nfunction length gate: limit {limit}, longest {longest[0]} ({longest[2]} {longest[1]})"
    )
    for name, reason in sorted(allowed.items()):
        # Printed every run: an exemption nobody sees is an exemption nobody revisits.
        print(f"  allowlisted  {name:28} {reason}")
    for count, where, name in over:
        print(f"  TOO LONG     {name:28} {count} lines at {where}", file=sys.stderr)
    return 1 if over else 0


def main(buckets: dict | None = None, totals: dict | None = None, strict: bool = False) -> int:
    """Print the bucket table. Caps REPORT unless `strict` (sprint rule, 2026-10-12).

    `buckets`/`totals` are injectable for tests.
    """
    if buckets is None:
        buckets, totals = load_buckets(), load_totals() if totals is None else totals
    totals = totals or {}
    print(f"{'bucket':15} {'code':>6} {'cap':>6} {'ceil':>6} {'doc':>6} {'blank':>6} {'total':>6}")
    breached = []
    measured: dict[str, tuple[int, int, int]] = {}
    for name, spec in buckets.items():
        excluded = {ROOT / p for p in spec.get("exclude", ())}
        files = sorted({f for p in spec["patterns"] for f in ROOT.glob(p)} - excluded)
        counts = {
            k: sum(measure(f)[k] for f in files)
            for k in ("code", "docstring", "comment", "blank", "total")
        }
        code = counts["code"]
        capped = spec.get("capped", True)
        cap, ceiling = (spec["cap"], spec["ceiling"]) if capped else (0, 0)
        measured[name] = (code, cap, ceiling) if capped else (code, 0, 0)
        # A ceiling fails the build; the cap only warns. Between them is the band the gate report
        # has to justify -- a hard stop at the estimate would make every honest estimate a lie.
        flag = ""
        if capped and code > ceiling:
            flag = "  OVER CEILING"
            breached.append(f"{name}: {code} > ceiling {ceiling}")
        elif capped and code > cap:
            flag = "  WARN over cap"
        print(
            f"{spec.get('label', name):15} {code:>6} {cap if capped else '-':>6} "
            f"{ceiling if capped else '-':>6} {counts['docstring']:>6} "
            f"{counts['blank']:>6} {counts['total']:>6}{flag}"
        )

    # Reported sums. They cannot FAIL independently -- a sum can only exceed the sum of the
    # ceilings if a member already exceeded its own -- so enforcing them would add nothing. They
    # are printed because a bucket split for sound design reasons still has to show its whole
    # cost: three small caps read as three small costs otherwise (team condition, 2026-10-12).
    for label, members in totals.items():
        rows = [measured[m] for m in members if m in measured]
        code, cap, ceiling = (sum(column) for column in zip(*rows, strict=True))
        print(f"{label:15} {code:>6} {cap:>6} {ceiling:>6} {'':>6} {'':>6} {'':>6}  (reported)")

    for message in breached:
        print(f"OVER A REPORTED CAP -- {message}", file=sys.stderr)
    if breached and not strict:
        print(
            "Caps are REPORTED, not blocking (sprint rule, expires at progress-v1). The blocking "
            "gates are ruff C901 and the function length gate below.",
            file=sys.stderr,
        )
    return 1 if (breached and strict) else 0


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    status = main(strict=strict)
    if "--no-functions" not in sys.argv:
        status |= check_functions()
    raise SystemExit(status)
