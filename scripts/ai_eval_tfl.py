"""Agree/disagree check: ProofPilot's own entailment pipeline against the AI-generated TFL
evaluation sets in data/eval/.

    python scripts/ai_eval_tfl.py           # print the report
    python scripts/ai_eval_tfl.py --write   # also write docs/experiments/ai_eval_tfl.md

These two files are an **AI-generated evaluation set** -- every item is tagged
`"source": "AI-generated (Claude)"`. This is never `data/heldout_paragraphs.json`, which stays
human-written and unwritten (CLAUDE.md rule 6); this script does not touch that file and never
will.

The simple tier carries an `expected_follows` ground truth per item, so this script can check the
system's own entailment verdict against it. The stress tier has no such field -- it is 15 sets of
harder per-sentence translation drills with no paragraph-level conclusion at all -- so there is
nothing to agree or disagree about there; this script reports its item count honestly rather than
inventing a comparison it has no ground truth for.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report import markdown_table, stamp_line  # noqa: E402
from src.core.entail import Verdict  # noqa: E402
from src.core.session import analyse  # noqa: E402

SIMPLE = ROOT / "data" / "eval" / "tfl_simple_tier_15.json"
STRESS = ROOT / "data" / "eval" / "tfl_stress_set_15.json"
OUT = ROOT / "docs" / "experiments" / "ai_eval_tfl.md"


def evaluate_one(item: dict) -> dict:
    """Run the real pipeline on one item and compare to its AI-authored `expected_follows`.

    `None` for `agree` means there is nothing to compare: a sentence refused to parse, or the
    premises were inconsistent, which the item's binary `expected_follows` cannot express.
    """
    found = analyse(item["paragraph"], item["conclusion"]["english"])
    verdict = found.entailment.verdict if found.entailment else None
    if verdict in (None, Verdict.INCONSISTENT_PREMISES):
        got = "PARSE_FAILURE" if verdict is None else verdict.value
        return {"id": item["id"], "theme": item["theme"], "got": got, "agree": None}
    got = verdict is Verdict.ENTAILED
    return {
        "id": item["id"],
        "theme": item["theme"],
        "got": got,
        "agree": got == item["expected_follows"],
    }


def render(results: list[dict], stress_count: int) -> str:
    scored = [r for r in results if r["agree"] is not None]
    agreeing = sum(r["agree"] for r in scored)
    lines = [
        "# AI-generated TFL evaluation set -- agreement with ProofPilot's own entailment check",
        "",
        stamp_line(),
        "",
        "**Source: AI-generated evaluation set** (`data/eval/tfl_simple_tier_15.json`, "
        '`data/eval/tfl_stress_set_15.json`; every item tagged `"source": "AI-generated '
        '(Claude)"`). This is not `data/heldout_paragraphs.json`, which stays human-written and '
        "unwritten (CLAUDE.md rule 6) and is never read by this script.",
        "",
        "## Simple tier: entailment agreement",
        "",
        f"**{agreeing}/{len(scored)} agree** with the item's `expected_follows` "
        f"({len(results) - len(scored)} not scorable -- parse failure or inconsistent premises).",
        "",
        markdown_table(
            ["id", "theme", "system verdict", "agree"],
            [
                [
                    str(r["id"]),
                    r["theme"],
                    str(r["got"]),
                    "N/A" if r["agree"] is None else ("yes" if r["agree"] else "NO"),
                ]
                for r in results
            ],
        ),
        "",
        "## Stress tier",
        "",
        f"**{stress_count} items**, each a set of harder per-sentence translation drills with no "
        "paragraph-level conclusion and no `expected_follows` field -- there is nothing to agree "
        "or disagree about here, so none is reported. Per `docs/report/FACTS.md`, neither file "
        "has had a human review pass for topical plausibility yet.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    simple = json.loads(SIMPLE.read_text(encoding="utf-8"))
    stress = json.loads(STRESS.read_text(encoding="utf-8"))
    results = [evaluate_one(item) for item in simple]
    text = render(results, len(stress))
    print(text)
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
