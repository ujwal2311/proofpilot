"""Analyse docs/pilot/template.csv: counts and medians only (HLD section 11, pilot E5).

No significance test at N<=10 -- a frozen design decision, not something this script works
around. Read-only: it never writes a row, only a report over whatever the facilitator recorded.

    python scripts/analyze_pilot.py           # print the report
    python scripts/analyze_pilot.py --write   # also write docs/pilot/results.md
"""

import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import markdown_table, stamp_line  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "pilot" / "template.csv"
OUT = ROOT / "docs" / "pilot" / "results.md"

NUMERIC = (
    "pre_test_score",
    "post_test_score",
    "ease_rating",
    "clarity_rating",
    "confidence_rating",
    "exercises_completed",
    "session_minutes",
)


def load_rows() -> list[dict[str, str]]:
    with TEMPLATE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def medians(rows: list[dict[str, str]]) -> dict[str, str]:
    """The median of each numeric column, over the rows that actually filled it in."""
    result = {}
    for column in NUMERIC:
        values = [float(row[column]) for row in rows if row[column].strip()]
        result[column] = f"{statistics.median(values):g}" if values else "—"
    return result


def code_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    """How often each feedback code appeared in `codes_seen`, across all participants."""
    counts: dict[str, int] = {}
    for row in rows:
        for code in row["codes_seen"].split(";"):
            code = code.strip()
            if code:
                counts[code] = counts.get(code, 0) + 1
    return counts


def render(rows: list[dict[str, str]]) -> str:
    stats = medians(rows)
    counts = code_counts(rows)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    lines = [
        "# ProofPilot pilot results (E5)",
        "",
        stamp_line(),
        "",
        f"**N = {len(rows)} participants.** Counts and medians only — no significance test",
        "is run at this sample size (HLD section 11), and none should be added by hand.",
        "",
        "## Medians",
        "",
        markdown_table(["metric", "median"], [[column, stats[column]] for column in NUMERIC]),
        "",
        "## Feedback codes seen, by frequency",
        "",
    ]
    if ranked:
        lines.append(markdown_table(["code", "times seen"], [[c, str(n)] for c, n in ranked]))
    else:
        lines.append("No codes recorded yet.")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    text = render(load_rows())
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
