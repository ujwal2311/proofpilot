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
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    counts = {"total": len(lines), "blank": sum(1 for ln in lines if not ln.strip())}
    counts["comment"] = sum(1 for ln in lines if ln.strip().startswith(("#", "//")))
    counts["docstring"] = 0
    if path.suffix == ".py":  # tokenize is Python-only; JS/CSS comments are counted above
        for token in tokenize.generate_tokens(iter(lines_with_ends(text)).__next__):
            if token.type == tokenize.STRING and token.line.strip().startswith(('"""', "'''")):
                counts["docstring"] += token.end[0] - token.start[0] + 1
    counts["code"] = counts["total"] - counts["blank"] - counts["comment"] - counts["docstring"]
    return counts


def lines_with_ends(text: str) -> list[str]:
    return [line + "\n" for line in text.splitlines()] + [""]


def main() -> int:
    print(
        f"{'bucket':12} {'code':>6} {'cap':>6} {'doc':>6} {'comment':>8} {'blank':>6} {'total':>6}"
    )
    breached = []
    for name, (patterns, cap) in BUCKETS.items():
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
