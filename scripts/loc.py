"""Report code lines per budget bucket and fail if a cap is exceeded.

Caps bound logic complexity, so they count CODE lines only: docstrings and WHY-comments are
required by CLAUDE.md rule 9 and improve explainability, so penalising them would be backwards.
Docstrings are found with `tokenize`, never regex -- a regex cannot tell a docstring from a
string literal that merely starts a line.
"""

import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUCKETS = {
    "core": (["backend/src/core/*.py"], 650),
    "api + cli": (["backend/src/api/*.py", "backend/src/cli.py"], 250),
    "scripts": (["scripts/*.py"], 180),
    "frontend": (["frontend/src/**/*.js", "frontend/src/**/*.jsx", "frontend/src/**/*.css"], 550),
}


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


def main(buckets: dict | None = None) -> int:
    """Print the table; return 1 if any cap is breached. `buckets` is injectable for tests."""
    buckets = BUCKETS if buckets is None else buckets
    print(
        f"{'bucket':12} {'code':>6} {'cap':>6} {'doc':>6} {'comment':>8} {'blank':>6} {'total':>6}"
    )
    breached = []
    for name, (patterns, cap) in buckets.items():
        files = sorted({f for p in patterns for f in ROOT.glob(p)})
        totals = {
            k: sum(measure(f)[k] for f in files)
            for k in ("code", "docstring", "comment", "blank", "total")
        }
        flag = "  OVER" if totals["code"] > cap else ""
        if flag:
            breached.append(f"{name}: {totals['code']} > {cap}")
        print(
            f"{name:12} {totals['code']:>6} {cap:>6} {totals['docstring']:>6} "
            f"{totals['comment']:>8} {totals['blank']:>6} {totals['total']:>6}{flag}"
        )
    for message in breached:
        print(f"BUDGET EXCEEDED -- {message}", file=sys.stderr)
    return 1 if breached else 0


if __name__ == "__main__":
    raise SystemExit(main())
