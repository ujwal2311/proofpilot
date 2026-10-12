"""The §11 evaluation suite: the BKT stopping-rule simulation, T2 hint soundness, T3 search cost.

    python scripts/run_experiments.py           # print every table
    python scripts/run_experiments.py --write   # also write docs/results.png,
                                                  # docs/results_simulation.csv,
                                                  # docs/experiments/run_experiments.md

T1 (held-out parser generalisation) is a separate script, `heldout_eval.py` — it depends on
`data/heldout_paragraphs.json`, which this project does not write (CLAUDE.md rule 6).

## The simulation (HLD section 11's one graph)

Three arms, each 500 simulated learners, one BKT-tracked skill per learner. Simulating one skill
rather than the real system's three is a documented simplification, not a shortcut: the three
skills update independently under identical BKT dynamics (`bkt.update` has no cross-skill term),
so three skills are statistically three times the learners of one, not a different experiment.

Each learner has a TRUE hidden mastery state that the model never observes directly, only through
simulated answers (correct with probability `1 - true_slip` once truly mastered, `true_guess`
before). The model's BELIEF is updated with `bkt.update` using the SHIPPED parameters
(`BktParams.from_config()`) in every arm — the model never changes; what changes is whether the
simulated learner's TRUE generative process matches it.

  * **baseline (fixed-N):** no belief, no stopping rule — every learner gets exactly N
    opportunities, where N = round(mean exercises the adaptive-matched arm actually used). This is
    what "a matched budget" means: the SAME total practice, spent without an early-stop rule.
  * **adaptive-matched:** stops once the model's belief reaches the threshold. The learner's TRUE
    generative parameters equal the model's assumed ones — the self-consistent case.
  * **adaptive-mismatched:** same stopping rule, but the TRUE generative process is a noisier,
    slower learner than the model assumes (`true_slip`, `true_transit` below). A DESIGN DECISION,
    not a measurement — one plausible misspecification, chosen to show the rule is not merely
    correct when the model happens to be right about the student.

**Metric: the premature-release rate** — % of learners released (stopped) while their TRUE hidden
state was still "not mastered". Not mean exercises (the baseline's N is defined to match the
adaptive-matched mean, so that bar would be equal by construction) and not final mastery at a
fixed budget (which averages away exactly the slow-learner cutoff the stopping rule exists to
catch). Mean exercises and mean over-practice (exercises spent after the learner's true mastery
point) are reported in the CSV and the figure caption, not as additional bars.

**Caveat, stated in the caption:** this tests only the stopping rule under the model's own
assumptions about what a learner's correctness distribution looks like — partly mitigated by the
mismatched run, but still a simulation, not a measurement of real students.
"""

import csv
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report import markdown_table, stamp_line  # noqa: E402
from src.app.data import load_bank  # noqa: E402
from src.core import config, search, tutor  # noqa: E402
from src.core.bkt import BktParams, update  # noqa: E402
from src.core.entail import Verdict  # noqa: E402
from src.core.session import analyse  # noqa: E402

N_LEARNERS = 500
WALK_CAP = 50  # opportunities per simulated learner, well past the ~8 the model needs to converge
RESULTS_PNG = ROOT / "docs" / "results.png"
RESULTS_CSV = ROOT / "docs" / "results_simulation.csv"
RESULTS_MD = ROOT / "docs" / "experiments" / "run_experiments.md"

# The mismatched arm's TRUE generative parameters. DESIGN DECISION (not fitted, not measured):
# a student who slips more often and learns a bit more slowly than the model assumes.
MISMATCH_SLIP = min(config.BKT_SLIP + 0.15, 0.49)
MISMATCH_TRANSIT = max(config.BKT_TRANSIT - 0.07, 0.01)


@dataclass(frozen=True)
class LearnerResult:
    exercises: int
    premature: bool
    over_practice: int


def model_params() -> BktParams:
    return BktParams.from_config()


def _mastered_at_step(rng: random.Random, true_p0: float, true_transit: float) -> int | None:
    """0 if already mastered, the 1-based opportunity it happens at, or None within WALK_CAP."""
    if rng.random() < true_p0:
        return 0
    for step in range(1, WALK_CAP + 1):
        if rng.random() < true_transit:
            return step
    return None


def simulate_adaptive(true: BktParams, model: BktParams, rng: random.Random) -> LearnerResult:
    """One learner under the adaptive stopping rule: stop once the MODEL's belief clears the bar."""
    mastered_at = _mastered_at_step(rng, true.p0, true.transit)
    belief = model.p0
    exercises = 0
    while belief < model.threshold and exercises < WALK_CAP:
        exercises += 1
        truly_mastered = mastered_at is not None and mastered_at <= exercises
        correct = rng.random() < ((1 - true.slip) if truly_mastered else true.guess)
        belief = update(belief, correct, model)
    truly_mastered = mastered_at is not None and mastered_at <= exercises
    over_practice = max(0, exercises - mastered_at) if truly_mastered else 0
    return LearnerResult(exercises, not truly_mastered, over_practice)


def simulate_baseline(true: BktParams, n: int, rng: random.Random) -> LearnerResult:
    """One learner given exactly `n` opportunities, with no stopping rule at all."""
    mastered_at = _mastered_at_step(rng, true.p0, true.transit)
    truly_mastered = mastered_at is not None and mastered_at <= n
    over_practice = max(0, n - mastered_at) if truly_mastered else 0
    return LearnerResult(n, not truly_mastered, over_practice)


def summarize(results: list[LearnerResult]) -> dict[str, float]:
    return {
        "premature_release_pct": 100 * sum(r.premature for r in results) / len(results),
        "mean_exercises": statistics.mean(r.exercises for r in results),
        "mean_over_practice": statistics.mean(r.over_practice for r in results),
    }


def run_simulation() -> dict[str, dict[str, float]]:
    """The three arms, in the order the baseline's N depends on: matched, then baseline, then
    mismatched. Each arm draws from its own seeded stream so the arms cannot contaminate one
    another (CLAUDE.md rule 4: seed every generator from config.py)."""
    model = model_params()
    matched_rng = random.Random(config.RANDOM_SEED)
    matched = [simulate_adaptive(model, model, matched_rng) for _ in range(N_LEARNERS)]
    matched_summary = summarize(matched)

    baseline_n = round(matched_summary["mean_exercises"])
    baseline_rng = random.Random(config.RANDOM_SEED + 1)
    baseline = [simulate_baseline(model, baseline_n, baseline_rng) for _ in range(N_LEARNERS)]

    mismatch_true = BktParams(
        model.p0, model.guess, MISMATCH_SLIP, MISMATCH_TRANSIT, model.threshold
    )
    mismatch_rng = random.Random(config.RANDOM_SEED + 2)
    mismatched = [simulate_adaptive(mismatch_true, model, mismatch_rng) for _ in range(N_LEARNERS)]

    return {
        "baseline (fixed-N)": summarize(baseline) | {"n_exercises_fixed": baseline_n},
        "adaptive-matched": matched_summary,
        "adaptive-mismatched": summarize(mismatched),
    }


def write_figure(stats: dict[str, dict[str, float]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    arms = list(stats)
    rates = [stats[arm]["premature_release_pct"] for arm in arms]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(arms, rates, color=["#999999", "#2b6cb0", "#c05621"])
    ax.set_ylabel("premature-release rate (%)")
    ax.set_title("BKT stopping rule vs a fixed-length baseline")
    caption = (
        "mean exercises: "
        + ", ".join(f"{arm}={stats[arm]['mean_exercises']:.1f}" for arm in arms)
        + f"\nseed={config.RANDOM_SEED}, N={N_LEARNERS} learners/arm. Tests only the stopping"
        " rule under the model's own assumptions (partly mitigated by the mismatched run)."
    )
    fig.text(0.02, -0.02, caption, fontsize=6, va="top", wrap=True)
    fig.tight_layout()
    fig.savefig(RESULTS_PNG, bbox_inches="tight", dpi=150)
    plt.close(fig)


def write_csv(stats: dict[str, dict[str, float]]) -> None:
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["policy", "premature_release_pct", "mean_exercises", "mean_over_practice"])
        for arm, values in stats.items():
            writer.writerow(
                [
                    arm,
                    f"{values['premature_release_pct']:.2f}",
                    f"{values['mean_exercises']:.2f}",
                    f"{values['mean_over_practice']:.2f}",
                ]
            )


def hint_soundness(walks_per_exercise: int = 10) -> list[list[str]]:
    """T2: seeded random walks of valid steps; every level-3 hint must be valid and non-worsening.

    A failure here is a bug to fix, never a result to report (HLD section 11) -- so this raises
    rather than recording a failing row, and the caller is expected to fix core before shipping
    a table that claims the hints are sound.
    """
    exercises, _ = load_bank()
    rows = []
    for index, exercise in enumerate(exercises):
        found = analyse(exercise.paragraph, exercise.conclusion)
        if found.entailment.verdict is not Verdict.ENTAILED:
            continue
        checked = 0
        for walk in range(walks_per_exercise):
            # Python's hash() is randomised per process (PYTHONHASHSEED), so it cannot seed
            # anything that must reproduce across runs -- caught by a determinism check that ran
            # this script twice and diffed the output.
            rng = random.Random(config.RANDOM_SEED + index * walks_per_exercise + walk)
            board = frozenset([*found.kb, *found.goal])
            for _ in range(WALK_CAP):
                if search.EMPTY_CLAUSE in board:
                    break
                hint = tutor.plan_hint(board, Verdict.ENTAILED, 3)
                if hint.code == "HINT_3":
                    verdict = search.productive(board, board | {hint.resolvent})
                    assert verdict is not False, f"{exercise.id}: a level-3 hint made it worse"
                    checked += 1
                steps = search.candidate_steps(board)
                if not steps:
                    break
                board |= {rng.choice(steps)[2]}
        rows.append([exercise.id, str(walks_per_exercise), str(checked)])
    return rows


def search_cost(repeats: int = 5) -> list[list[str]]:
    """T3: per exercise, shortest proof length, states generated, median wall time, budget hits.

    `search.distance` requires entailment to have already been checked (it raises otherwise, by
    design — section 7's ordering), so a non-entailing exercise has no proof to search for and
    gets its own row rather than being skipped silently.
    """
    exercises, _ = load_bank()
    rows = []
    for exercise in exercises:
        found = analyse(exercise.paragraph, exercise.conclusion)
        if found.entailment.verdict is not Verdict.ENTAILED:
            rows.append([exercise.id, "does not entail", "—", "—", "—"])
            continue
        board = frozenset([*found.kb, *found.goal])
        times, exhausted, last_generated, last_len = [], 0, 0, None
        for _ in range(repeats):
            search.clear_distance_cache()
            work = search.Work(config.MAX_SEARCH_WORK)
            start = time.perf_counter()
            last_len = search.distance(board, work)
            times.append(time.perf_counter() - start)
            last_generated = config.MAX_SEARCH_WORK - work.left
            if last_len is None:
                exhausted += 1
        rows.append(
            [
                exercise.id,
                "—" if last_len is None else str(last_len),
                str(last_generated),
                f"{statistics.median(times) * 1000:.2f} ms",
                str(exhausted),
            ]
        )
    return rows


def render_markdown(stats: dict[str, dict[str, float]], hints: list, costs: list) -> str:
    lines = [
        "# Evaluation: simulation, hint soundness, search cost",
        "",
        stamp_line(),
        "",
        "Regenerate: `python scripts/run_experiments.py --write`.",
        "",
        "## Simulation (docs/results.png, docs/results_simulation.csv)",
        "",
        markdown_table(
            ["policy", "premature-release %", "mean exercises", "mean over-practice"],
            [
                [
                    arm,
                    f"{v['premature_release_pct']:.1f}",
                    f"{v['mean_exercises']:.1f}",
                    f"{v['mean_over_practice']:.1f}",
                ]
                for arm, v in stats.items()
            ],
        ),
        "",
        "## T2 — hint soundness (seeded random walks)",
        "",
        "Every level-3 hint checked was valid and non-worsening (section 6.6). A failure would",
        "raise during the run, not appear as a row here.",
        "",
        markdown_table(["exercise", "walks", "level-3 hints checked"], hints),
        "",
        "## T3 — search cost",
        "",
        markdown_table(
            ["exercise", "shortest proof", "states generated", "median time", "budget hits"],
            costs,
        ),
        "",
        "Machine-dependent: times are not comparable across machines; see",
        "docs/experiments/search_latency.md.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    stats = run_simulation()
    hints = hint_soundness()
    costs = search_cost()
    text = render_markdown(stats, hints, costs)
    print(text)
    if "--write" in argv:
        write_figure(stats)
        write_csv(stats)
        RESULTS_MD.write_text(text, encoding="utf-8")
        print(
            f"wrote {RESULTS_PNG.relative_to(ROOT)}, {RESULTS_CSV.relative_to(ROOT)}, "
            f"{RESULTS_MD.relative_to(ROOT)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
