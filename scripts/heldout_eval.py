"""T1: parser generalisation on held-out paragraphs (HLD section 11).

    python scripts/heldout_eval.py           # print the report
    python scripts/heldout_eval.py --write   # also write docs/experiments/heldout_eval.md

`data/heldout_paragraphs.json` is written by HUMANS, after the parser is frozen -- the student and
classmates, never by Claude (CLAUDE.md rule 6) -- and it is never used for tuning. This script only
reads it; if it has not been handed over yet, that is reported honestly, not faked.

Expected schema (fails loudly, never guesses, if a file does not match it):

    {
      "schema_version": 1,
      "paragraphs": [
        {"id": "h01", "topic": "...", "paragraph": "...", "conclusion": "..."},
        ...
      ]
    }

Per OQ3 (HLD section 11): a poor result does not block the report. Whatever this prints on the
FIRST run against the handed-over file is published as-is; any later parser fix gets its own
separate, labelled "after fixes" run -- this script never silently overwrites a first-run number.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report import markdown_table, stamp_line  # noqa: E402
from src.core.session import analyse  # noqa: E402

HELDOUT = ROOT / "data" / "heldout_paragraphs.json"
OUT = ROOT / "docs" / "experiments" / "heldout_eval.md"


class HeldoutSchemaError(ValueError):
    """The file exists but does not match the expected shape -- never guessed at, always named."""


def load_paragraphs() -> list[dict]:
    if not HELDOUT.is_file():
        return []
    payload = json.loads(HELDOUT.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "paragraphs" not in payload:
        raise HeldoutSchemaError(f"{HELDOUT}: expected a 'paragraphs' key, got {type(payload)}")
    for item in payload["paragraphs"]:
        missing = {"id", "paragraph", "conclusion"} - item.keys()
        if missing:
            raise HeldoutSchemaError(f"{item.get('id', '?')}: missing fields {missing}")
    return payload["paragraphs"]


def evaluate_one(item: dict) -> dict:
    """Run the real pipeline on one held-out paragraph. Never trains on it, only reports."""
    found = analyse(item["paragraph"], item["conclusion"])
    codes = [s.error_code for s in found.sentences if s.error_code]
    return {
        "id": item["id"],
        "sentences": len(found.sentences),
        "ok": sum(1 for s in found.sentences if s.status == "ok"),
        "fully_parsed": all(s.status == "ok" for s in found.sentences),
        "error_codes": codes,
        "facts": len(found.facts),
    }


def aggregate(results: list[dict]) -> dict:
    total_sentences = sum(r["sentences"] for r in results)
    total_ok = sum(r["ok"] for r in results)
    code_counts: dict[str, int] = {}
    for r in results:
        for code in r["error_codes"]:
            code_counts[code] = code_counts.get(code, 0) + 1
    return {
        "n_paragraphs": len(results),
        "pct_sentences_parsed": 100 * total_ok / total_sentences if total_sentences else 0.0,
        "pct_paragraphs_fully_parsed": (
            100 * sum(r["fully_parsed"] for r in results) / len(results) if results else 0.0
        ),
        "error_codes": code_counts,
        "mean_facts_per_paragraph": (
            sum(r["facts"] for r in results) / len(results) if results else 0.0
        ),
    }


def render(results: list[dict], totals: dict) -> str:
    lines = [
        "# Held-out parser generalisation (T1)",
        "",
        stamp_line(),
        "",
    ]
    if not results:
        lines += [
            "**Not yet run.** `data/heldout_paragraphs.json` has not been handed over -- it is",
            "written by humans after the parser is frozen, never by Claude, and never used for",
            "tuning (HLD section 11, CLAUDE.md rule 6).",
        ]
        return "\n".join(lines) + "\n"
    lines += [
        f"**N = {totals['n_paragraphs']} held-out paragraphs.** First-run numbers — a poor result",
        "does not block the report (OQ3); a later parser fix gets its own separate, labelled run.",
        "",
        f"- **{totals['pct_sentences_parsed']:.1f}%** of sentences parsed",
        f"- **{totals['pct_paragraphs_fully_parsed']:.1f}%** of paragraphs fully parsed",
        f"- **{totals['mean_facts_per_paragraph']:.1f}** facts per paragraph on average — the",
        "  count a human reviewer checks for ones that should have been manually merged; this",
        "  script reports the count only, never an automated merge verdict (HLD section 12: manual",
        "  merge only)",
        "",
        "## Error codes seen",
        "",
    ]
    ranked = sorted(totals["error_codes"].items(), key=lambda item: (-item[1], item[0]))
    lines.append(
        markdown_table(["code", "count"], [[c, str(n)] for c, n in ranked])
        if ranked
        else "None — every sentence parsed."
    )
    lines += [
        "",
        "## Per paragraph",
        "",
        markdown_table(
            ["id", "sentences", "ok", "fully parsed", "facts"],
            [
                [
                    r["id"],
                    str(r["sentences"]),
                    str(r["ok"]),
                    str(r["fully_parsed"]),
                    str(r["facts"]),
                ]
                for r in results
            ],
        ),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    results = [evaluate_one(item) for item in load_paragraphs()]
    totals = aggregate(results)
    text = render(results, totals)
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
