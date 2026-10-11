"""Report code lines per budget bucket and fail if a ceiling is exceeded.

Caps bound logic complexity, so they count CODE lines only: docstrings and WHY-comments are
required by CLAUDE.md rule 9 and improve explainability, so penalising them would be backwards.
Docstrings are found with `tokenize`, never regex -- a regex cannot tell a docstring from a
string literal that merely starts a line.

The numbers come from `budgets.toml` and appear nowhere else (v2.10). Each bucket has a `cap`,
which is the frozen bottom-up estimate and warns, and a `ceiling` of cap + 10%, which fails. A
bucket may be `capped = false` to be reported without a limit, and may `exclude` paths its
pattern would otherwise swallow -- `core` and `core_m2` live in one directory and must not be
measured against each other's cap (v2.11).
"""

import sys
import tokenize
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = ROOT / "budgets.toml"


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


def measure(path: Path) -> dict[str, int]:
    """Classify every line into exactly ONE bucket.

    Counting the buckets independently double-counts a blank line inside a docstring, which
    subtracts it twice and silently inflates the code allowance. Each line is labelled once,
    docstring first, so the four buckets always sum to the total.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    label = [""] * len(lines)

    if path.suffix == ".py":  # tokenize is Python-only; JS/CSS comments are handled below
        for token in tokenize.generate_tokens(iter(lines_with_ends(text)).__next__):
            if token.type == tokenize.STRING and token.line.strip().startswith(('"""', "'''")):
                for row in range(token.start[0] - 1, token.end[0]):
                    label[row] = "docstring"

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


def main(buckets: dict | None = None, totals: dict | None = None) -> int:
    """Print the table; return 1 if any ceiling is breached. Injectable for tests."""
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
        print(f"BUDGET EXCEEDED -- {message}", file=sys.stderr)
    return 1 if breached else 0


if __name__ == "__main__":
    raise SystemExit(main())
