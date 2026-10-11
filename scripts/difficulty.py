"""Compute each exercise's difficulty band from its SHORTEST PROOF, and write data/difficulty.json.

Difficulty is derived, never declared (HLD v2.8 A4a). A hand-written band is a number nobody can
check: it would survive an edit to the paragraph, an edit to the conclusion, and a change to
`search`, and band selection, the simulation and the results table would all inherit it silently.
So the only difficulty in the repository is the output of this script, and CI re-runs it and diffs
the result (HLD section 17.1.1, blocking item B1).

Bands come from HLD section 9: proof length 2 -> short, 3 -> medium, 4-5 -> long. An exercise whose
conclusion does not follow has no proof, so it is banded `short` -- deciding "it does not follow"
is the one-step action the ladder in section 6.6.1 coaches, not a long derivation.

    python scripts/difficulty.py          # write data/difficulty.json
    python scripts/difficulty.py --check  # exit 1 if the committed file is stale (CI uses this)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from src.app.data import BANDS_PATH, SCHEMA, load_bank  # noqa: E402
from src.core import search, session  # noqa: E402  (needs the path above)
from src.core.entail import Verdict  # noqa: E402

# Proof length -> band. Inclusive upper bounds, longest last, so a proof deeper than the bank is
# supposed to contain still lands somewhere rather than raising.
LADDER = ((2, "short"), (3, "medium"))


def band_of(steps: int | None) -> str:
    """The band for a shortest-proof length. `None` means the conclusion does not follow."""
    if steps is None:
        return "short"
    for limit, band in LADDER:
        if steps <= limit:
            return band
    return "long"


def compute() -> dict[str, str]:
    """Band every exercise in the bank, in id order so the output file is byte-stable."""
    exercises, _ = load_bank()
    bands = {}
    for exercise in sorted(exercises, key=lambda e: e.id):
        found = session.analyse(exercise.paragraph, exercise.conclusion)
        if found.entailment.verdict is not Verdict.ENTAILED:
            bands[exercise.id] = band_of(None)
            continue
        # The cache is cleared per exercise so the measured distance is the exercise's own cost
        # and not an artefact of whichever exercise ran before it.
        search.clear_distance_cache()
        bands[exercise.id] = band_of(search.distance(frozenset([*found.kb, *found.goal])))
    return bands


def render(bands: dict[str, str]) -> str:
    """The file's exact bytes. One function, so writing and checking cannot disagree."""
    payload = {
        "schema_version": SCHEMA,
        "_README": "DERIVED by scripts/difficulty.py from the shortest proof. Never edit by hand.",
        "bands": bands,
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(compute())
    if "--check" in argv:
        committed = BANDS_PATH.read_text(encoding="utf-8") if BANDS_PATH.is_file() else ""
        if committed == text:
            return 0
        print("STALE: data/difficulty.json does not match the bank.", file=sys.stderr)
        print("Run `python scripts/difficulty.py` and commit the result.", file=sys.stderr)
        return 1
    BANDS_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {BANDS_PATH.relative_to(ROOT)}")
    for exercise_id, band in compute().items():
        print(f"  {exercise_id}  {band}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
