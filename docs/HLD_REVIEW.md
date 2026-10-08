# ProofPilot HLD — Adversarial Design Review

Reviewer stance: principal engineer, assume `docs/HLD.md` (v1.0, 256 lines) is wrong until proven
otherwise. No code written. No edits made to the HLD in this pass.

**Note on inputs:** `CLAUDE.md` does not exist yet — it is a Phase 1 deliverable. Per the project
brief, Phase 1 will copy the INTEGRITY / PROJECT / HARD CONSTRAINTS / ENGINEERING RULES / SPEC
sections of the original prompt verbatim into `CLAUDE.md`. I am treating those sections, as given
in the original prompt, as the requirements baseline this review traces against. If anything below
reads as "the spec is wrong," I've said so explicitly rather than silently picking a side.

---

## 1. VERDICT: **GO-WITH-FIXES**

**6 BLOCKER, 12 MAJOR, 6 MINOR.**

None of the blockers requires an architecture change — all 6 are documentation/contract gaps
(undefined behavior for a real scenario, or a design choice that would silently corrupt a file or
stall a demo) fixable by editing `docs/HLD.md` itself, not by redesigning anything. That's why this
is GO-WITH-FIXES and not NO-GO: the bones are sound, but several load-bearing decisions were left
as bare function signatures with no behavior spelled out, and those gaps land exactly where the
biggest planned experiment (E4, 500 simulated learners) and the live viva will stress the system
hardest.

**Top 3 risks, ranked by how likely they are to actually bite:**

1. **B1/B6 — exercise-selection fallback/repeat policy is undefined.** With only 12 exercises and
   500 synthetic learners in E4, the bank *will* be exhausted and bands *will* tie. There is
   currently no deterministic rule for either case, which threatens `test_simulation_deterministic_with_seed`
   directly and is the first question any examiner will ask in the viva.
2. **B4 — search cost at the 20-clause cap.** `C(20,2)=190` clause pairs per BFS level means a
   student who free-explores for a few minutes (entirely plausible, even desirable, behavior) can
   make hints slow or cap-out *during the live demo*, and the HLD currently treats the 20-clause
   cap as the fix for this risk when it is actually the thing that makes the branching large.
3. **B2 — `difficulty.py` writing back into `domain.yaml`.** Plain PyYAML dumping does not
   preserve comments on a round-trip. The very first run of this script would silently delete the
   spec-mandated "parameters are ASSUMED, not fitted" comment — a self-inflicted integrity-adjacent
   bug triggered by the design's own tooling.

---

## 2. FINDINGS TABLE

| ID | Sev | Pass | HLD location | Quoted text | Problem | Fix | Cost |
|---|---|---|---|---|---|---|---|
| B1 | BLOCKER | 4,5,14 | §5 L117 | `next_exercise(mastery: dict, done_ids, exercises: list[Exercise])` | "Fall back to the nearest band" has no tie-break when two bands are equidistant from the target (e.g. mean mastery 0.4, medium exhausted, short/long both unseen) — a real case with only 12 exercises across 3 bands | State the rule: ties broken toward the easier (lower-difficulty) band | 20 min doc |
| B2 | BLOCKER | 2,9,10 | §3 L52 | "writes it back for `tutor.py`'s band lookup" | Round-tripping `domain.yaml` through a plain YAML dump (the only YAML lib in the approved dependency list is PyYAML) discards comments, including the spec-required "parameters are ASSUMED" note, on the very first run | Compute difficulty in-memory at process start (cache), never mutate `domain.yaml`; `difficulty.py` becomes a pure reporting script for E2 | 0 (net simpler than current plan) |
| B3 | BLOCKER | 3 | §5 L117 | `exercises: list[Exercise]` | `Exercise` is referenced in a signature but its shape and the module that parses `data/domain.yaml` into it are never defined anywhere in the document | Add an `Exercise` dataclass to §4 (id, clauses, goal, symbols, difficulty_band) and name its owning module | 20 min doc |
| B4 | BLOCKER | 4,8 | §9 L182 | "API caps clauses ≤20, literals ≤6" listed as the *prevention* for search blow-up | The 20-clause cap is what *creates* the C(20,2)=190-pair branching per BFS level, not what prevents it; also undefined: what happens when a valid, productive step is found at exactly 20 clauses (append the 21st, or refuse)? | Benchmark a deliberately-polluted ~20-clause state in Phase 3 (not just the 3 clean fixtures) and set `max_nodes` from that measurement; document the monotonic-distance invariant (adding clauses never increases distance-to-goal); decide and document that a step found at the cap is refused with 400 as an intentional, documented dead end | 1–2 h (benchmark already planned for Phase 3) + 20 min doc |
| B5 | BLOCKER | 5 | §6 L127 | `{state, done}` | `solved` (one exercise's empty clause reached) and `done` (all-skills-mastered, session-level) are two different flags, never distinguished in prose; what `/api/next` returns in `state` when `done=true` is undefined | Add one paragraph distinguishing the two; specify `state` is returned unchanged (the last exercise's final state) when `done=true` | 15 min doc |
| B6 | BLOCKER | 4,5,14 | §5 L117 | same signature as B1 | Once "allow repeats only once the bank is exhausted" triggers, the spec gives no selection order among the now-all-seen 12 exercises — undefined for every simulated learner that runs long enough in E4 | Define repeat order: least-recently-seen, ties broken by lowest ID | 20 min doc (shared edit location with B1) |
| M1 | MAJOR | 1,12 | §10 L209 | "backend subtotal (excl. tests) ~675 ... within ≤700 budget" | The original constraint lists "core ≈300–450" and "backend excl. tests ≤700" as two separate bullets; §10 folds core *into* the 700, landing at 675/700 with ~0 slack. Ambiguous either reading, risky either way | Ask the student which reading is intended (Open Q2); restate §10 unambiguously once answered | 20 min doc, pending answer |
| M2 | MAJOR | 12 | §10 L201–205 | "core subtotal ~355" | Re-estimating `diagnose()`'s closest-resolvent logic, `next_exercise`'s full chain, and BFS's cap+cache handling individually puts core closer to ~420–480 lines — already brushing the 450 ceiling before Phase 2 starts | Revise estimates upward now; flag explicitly that core may land at the high end, to be justified (not discovered as a surprise) at the Phase 2 gate per Engineering Rule 2 | 0 (awareness only) |
| M3 | MAJOR | 12 | §10 L210 | "frontend/src (all components + api.js) ~390" | One aggregate number for 7+ files makes the ≤400 ceiling unauditable from the document as written | Break into per-file estimates (App.jsx, ExercisePanel, ResolventInput, FeedbackBox, MasteryBars, api.js, index.css, main.jsx) | 15 min doc |
| M4 | MAJOR | 1,12 | whole doc | (absent) | No hour estimate appears anywhere, despite the explicit ~46-hour constraint — nothing to check feasibility against, and the team is 2 people (see Open Q1) | Add a rough phase-by-phase hour table, explicitly labeled a planning estimate, not a measured result | 15 min doc |
| M5 | MAJOR | 4 | §5 L115 | `evidence_for(code, productive, hinted) -> dict[Skill, bool]` | "Every hint used ⇒ observed skill counts as wrong" is only inferable from a test's *name* (`test_observation_mapping_skips_unobserved`); the alternative reading ("all three skills, even unobserved, forced wrong") is equally plausible from the prose and currently undisambiguated | Add the explicit combined (code × productive × hinted) table to §5 or §7 | 20 min doc |
| M6 | MAJOR | 6,8 | §5 L101 | `distance(state, max_nodes) -> int \| None` | Spec requires "cache results by state"; HLD never specifies cache key (state alone vs state+max_nodes), eviction, or that `None` must never be cached (it's cap-value-dependent — a cached `None` from a low cap would wrongly short-circuit a later call with a higher cap) | Add 2–3 sentences: cache only confirmed (non-`None`) distances, keyed by state alone; unbounded-but-small growth is fine for a short-lived dev/demo process | 15 min doc |
| M7 | MAJOR | 9 | §6 L143–145 | "level 2 names both clause IDs" | Hints translate `best_next_step`'s returned clause *content* back into clause *IDs* via reverse lookup; this silently depends on the invariant that no two clauses in state ever share content — enforced today only as a side-effect of the DUPLICATE check, never stated as an invariant the API relies on | State the invariant explicitly; confirm `test_hint_pair_is_valid_per_core` (or a dedicated test) actually covers it | 15 min doc |
| M8 | MAJOR | 10 | §8 L169 | `\| Decision \| Pros \| Cons \| Chosen \|` | None of the 6 decision rows notes reversibility, despite being asked for explicitly | Add a reversibility phrase per row | 20 min doc |
| M9 | MAJOR | 5,6 | §8 L176 | "discards and restarts on any mismatch" | No schema-versioning mechanism exists; a `State` shape change in a later phase leaves old cached JSON that may simply be missing new fields rather than failing an obvious "mismatch" check | Store a `schemaVersion` constant alongside state in localStorage; discard on any version mismatch or absence | 15 min doc (implementation is ~5 lines, already in frontend budget) |
| P1 | MAJOR | 11 | §9 (table) | (missing row) | No pre-mortem risk names the live-demo consequence of B4 specifically (slow/cap-hit hint *on stage*, not just in the abstract) | Add a "demo day" risk row | 10 min doc |
| P2 | MAJOR | 11,12 | §9 (table) | (missing row) | No risk row covers the 46-hour/team-size ambiguity (M4, Open Q1) as a schedule risk | Add a "schedule" risk row | 10 min doc |
| P3 | MAJOR | 11,14 | §9 (table) | (missing row) | No risk row covers the viva-specific exposure of B1/B6 (exam­iner asks "what happens when the bank runs out?" with no defined answer) | Add a "viva readiness" risk row | 10 min doc |
| N1 | MINOR | 4 | §5 L97 | `diagnose(a, b, claimed, existing: frozenset[Clause])` | Doesn't state whether `existing` includes `a` and `b` themselves (harmless either way — provably, a resolvent can never equal either parent — but worth saying so a reader doesn't have to re-derive it) | Add: "`existing` is the full current clause set, including `a` and `b`" | 5 min doc |
| N2 | MINOR | 4 | §11 L224–231 | item 2's non-collision proof | Only proves WRONG_RESOLVENT is unambiguous; doesn't extend the same argument to show DOUBLE_CANCEL never collides with TAUTOLOGY either (it doesn't — sizes differ structurally — but it isn't written down) | Extend item 2's proof by one sentence | 10 min doc |
| N3 | MINOR | 4 | §5 L101 | `distance(state, max_nodes) -> int \| None` | Base case (state already containing the empty clause ⇒ distance 0, no expansion) isn't stated | Add "(0 if the empty clause is already present)" | 5 min doc |
| N5 | MINOR | 6 | §5 L116 | `is_done(mastery, threshold: float = 0.95)` | Floating-point ties at band boundaries (0.4/0.8) or the 0.95 threshold aren't addressed (low real risk given continuous BKT updates, but unstated) | One line: comparisons are plain `<`/`>=` on floats; acceptable because BKT posteriors essentially never land exactly on a boundary | 5 min doc |
| N6 | MINOR | 13 | §8 L175 | "richer help-models (e.g. Baker et al.)" | An uncited, informal name-drop of a specific researcher inside an engineering doc risks later leaking into report prose without going through the verification process required for `references.md` | Replace with an unattributed phrase, e.g. "more sophisticated help-models in the ITS literature" | 5 min doc |
| N7 | MINOR | 5 | §6 L147–148 | "`available: false` with a `reason`" | Doesn't state that `state` (including `hint_level`) is left completely unchanged when a hint is unavailable — i.e. asking for a hint and being told no costs the student nothing | Add one clause making this explicit | 5 min doc |

---

## 3. TRACEABILITY TABLE

| Requirement (source) | HLD section | Proving test | Status |
|---|---|---|---|
| Core has zero fastapi/pydantic/web imports | §2, §3 | `test_core_has_no_web_imports` | COVERED |
| API is a thin 4-endpoint layer | §6 | `test_health_ok` + others | COVERED |
| React has no AI logic | §3 (frontend row) | *(none named)* | PARTIAL — enforced by discipline/code review only, no automated guard |
| Code budget: core 300–450 | §10 | *(manual LOC count)* | PARTIAL — see M2, optimistic |
| Code budget: backend ≤700 excl. tests | §10 | *(manual LOC count)* | PARTIAL — see M1, ambiguous accounting |
| Code budget: frontend ≤400 | §10 | *(manual LOC count)* | PARTIAL — see M3, unauditable aggregate |
| Domain: 12 exercises, ≤4 symbols, ≤6 clauses, proof 2–5 | §3 (`domain.yaml` row) | `test_every_exercise_provable_within_cap` | COVERED at data level; `Exercise` type itself undefined — see B3 |
| DO-NOT-BUILD list (A*, SOS, parser, FOL, DB, Docker, …) | §8 (BFS vs A* row) | *(absence)* | COVERED |
| `normalize_literal` accepts `~P`, `¬P`, `" ~ p "` | §5 | *(no test named in the 16-test suite)* | PARTIAL — gap in the spec's own test list, not just the HLD |
| `resolvents()`: exactly one complementary pair | §5, §9 | `test_resolve_single_clash` | COVERED |
| Two clashes ⇒ only tautologies | §11 item 2 | `test_two_clashes_yield_only_tautologies` | COVERED |
| Diagnosis order NO_CLASH→…→VALID | §5 (`Code` enum), §11 item 2 | 4 named `test_diagnose_*` | COVERED |
| Negated goal = ONE clause | §5 (`negate_goal`) | *(no test named)* | PARTIAL — gap in the spec's own test list |
| BFS state/action/cost/goal/cache | §5 | `test_bfs_distance_fixture` | PARTIAL — cache semantics unspecified, see M6 |
| `distance` returns `None` at cap | §5 | `test_search_cap_returns_none_not_hang` | COVERED |
| `best_next_step` deterministic tie-break | §5 | *(no test named)* | PARTIAL — gap |
| `productive` ⇔ distance drops by exactly −1, `None` on cap | §5, §6 | `test_productive_iff_distance_drops_by_one` | COVERED |
| BKT correct/wrong formulas + validation | §5 (`BKTParams`) | `test_bkt_update_hand_example` | COVERED — independently re-verified, see §4 below |
| Evidence mapping (code × productive × hinted) | §5 (`evidence_for`) | `test_observation_mapping_skips_unobserved` | PARTIAL — combined table not written out, see M5 |
| `next_exercise`: unseen-first / band / fallback / repeat | §5 (signature only) | `test_simulation_deterministic_with_seed` | **VIOLATED/MISSING** — undefined behavior, see B1, B6 |
| Difficulty via BFS, never hand-labeled | §3 (`difficulty.py` row) | `test_every_exercise_provable_within_cap` (indirect) | AT RISK — mechanism risks corrupting `domain.yaml`, see B2 |
| API stateless, state round-tripped | §2, §6, §8 | implied by every API test passing `state` explicitly | COVERED |
| Clause IDs stable, append-only | §4, §9 risk 6 | *(no dedicated test named)* | COVERED at design level; untested |
| API limits: ≤20 clauses, ≤6 literals, regex, symbol-in-exercise | §6, §7 | `test_step_malformed_literal_returns_422` (regex only) | PARTIAL — count/symbol-domain limits have no named test |
| Error codes 400/404/409/422 fully mapped | §6 | only 422 has a named test | PARTIAL — 400/404/409 untested in the named 16-test suite |
| Hint idempotent replay / unavailable path | §6 | `test_hint_pair_is_valid_per_core` | PARTIAL — only checks hint validity, not idempotence or the cap-unavailable path |
| CORS both `localhost`/`127.0.0.1` | §9 risk 4 | *(manual check only)* | PARTIAL |
| CLI plays rain example end-to-end | §3 (cli row) | manual smoke run (Phase 5 hard gate) | COVERED by process, not pytest |
| AI_USAGE_LOG kept, references verified, no report prose | *(outside HLD.md)* | n/a | COVERED by process rule |
| ~46-hour effort budget | *(absent)* | n/a | **MISSING** — see M4 |
| Mermaid diagram renders on GitHub | §2 | visual check at commit time | COVERED |
| Determinism: no hash/dict-order dependence | §9 risk 2 | "tests assert exact ordering" (unnamed) | COVERED generally; `best_next_step` tie-break specifically ungoverned (see above) |

**Scope creep:** none significant found. The HLD under-specifies more than it over-builds. Two
small, *self-disclosed* additions exist (409 on `/api/hint` too, a defensive canonical-sort
tie-break for WRONG_RESOLVENT messaging) — both cheap, both already flagged in §11 of the HLD
itself, neither is a concern.

---

## 4. ALGORITHM RE-DERIVATION (Pass 4 detail)

- **BKT worked example**, independently recomputed:
  - Correct: `P'=0.3·0.9/(0.3·0.9+0.7·0.2) = 0.27/0.41 = 0.658537`; `P_next = 0.658537 + 0.341463·0.15 = 0.709756` → **0.7098** ✓.
  - Wrong: `P'=0.3·0.1/(0.3·0.1+0.7·0.8) = 0.03/0.59 = 0.050847`; `P_next = 0.050847 + 0.949153·0.15 = 0.193220` → **0.1932** ✓.
  - Both match the HLD's claimed values to 4 decimal places. The Bayes'-rule derivation is correct
    (`P(wrong|not mastered) = 1-g` is used correctly in the denominator).
- **Two-clash-pair theorem** (underlies B1's sibling finding, the WRONG_RESOLVENT non-ambiguity
  claim in HLD §11 item 2): confirmed by direct construction. `a={P,Q,R}, b={~P,~Q,R}` — pivoting
  on P gives `{Q,~Q,R}` (tautology), pivoting on Q gives `{P,~P,R}` (tautology); the double-cancel
  result `{R}` is neither, and sizes provably differ, so DOUBLE_CANCEL can never collide with a
  tautological single-pivot resolvent. HLD's claim holds; it just doesn't write down the general
  proof covering DOUBLE_CANCEL (N2).
- **BFS worst-case branching** (underlies B4): at a 20-clause state, `C(20,2)=190` candidate pairs
  per level; each pair yields at most `min(symbols in a, symbols in b) ≤ 4` resolvent candidates.
  Because every action strictly *adds* a clause, distance-to-goal from any reachable state is
  provably `≤` the original exercise's shortest-proof length (2–5) — but branching-factor blow-up
  at that cap can still make BFS visit thousands of nodes per level before finding the lucky
  witness path, independent of that depth bound. This is the crux of B4.
- **`g+s<1` constraint**: necessary (keeps denominators positive and the posterior inside (0,1))
  but not sufficient for identifiability (standard practice also wants `g,s<0.5`); HLD already
  flags this honestly in §11 item 3 — no new finding, confirmed correct as stated.

---

## 5. SCENARIO TABLE

| # | Scenario | Expected outcome | Defined in HLD? |
|---|---|---|---|
| a | Rain example, happy path | Chain of VALID+productive steps to `frozenset()`, `solved=true` | Y (mechanism defined; fixture numbers deferred to Phase 3, acceptable) |
| b | Non-clashing clauses picked | `NO_CLASH`, CLASH:wrong | Y |
| c | Double cancellation | `DOUBLE_CANCEL`, CLASH:right/RESOLVE:wrong | Y |
| d | Correct resolvent, unproductive | `VALID`, productive=False, STRATEGY:wrong | Y |
| e | Empty clause entered correctly | `VALID`, productive via `distance=0` base case | Y (base case undocumented — N3) |
| f | Hints 1→2→3, then step | hinted=True, every *observed* skill forced wrong, no per-level penalty tiering | Y, but combined table missing (M5) |
| g | Search cap hit during a hint | `available:false` + reason, `state` untouched | PARTIAL (mechanism Y; "state untouched" unstated — N7) |
| h | Browser refresh mid-exercise | localStorage reload; schema-version check | **N** (M9) |
| i | Step sent after solved | 409 | Y |
| j | Tampered state (unknown ID / foreign symbol / 50 clauses) | 400 for ID/symbol; 20-clause boundary with one more *valid* step undefined | PARTIAL (B4) |
| k | All skills ≥ threshold | `/api/next` returns `done=true`; `state` field contents undefined | PARTIAL (B5) |
| l | `uvicorn --reload` restarts mid-session | No effect — stateless design | Y |

---

## 6. PROPOSED HLD PATCH LIST (minimal, exact edits — BLOCKERS first)

1. **[B2]** §3, `scripts/difficulty.py` row: replace "writes it back for `tutor.py`'s band lookup"
   with "computed in-memory at process start and cached; never mutates `domain.yaml`;
   `difficulty.py` doubles as the E2 reporting script." Delete the write-back behavior everywhere
   it's implied.
2. **[B3]** §4: add an `Exercise` dataclass (`id`, `clauses`, `goal`, `symbols`,
   `difficulty_band`). §3: add an owner (a small loader, e.g. `core/exercises.py` or a function in
   `tutor.py`) for "parse `data/domain.yaml` → `Exercise` objects."
3. **[B1, B6]** §5, `next_exercise`: add the mean-mastery formula and the full selection chain in
   prose — unseen-in-target-band → unseen-in-nearest-band (ties broken toward the easier band) →
   repeat (least-recently-seen, ties broken by lowest ID).
4. **[B4]** §9 risk #1: rewrite the "Prevention" column to be honest about graceful degradation
   vs. prevention. §3/§7: add one sentence stating the monotonic-distance invariant. §6: add the
   decision that a valid step found at exactly 20 clauses is refused with 400, documented as an
   intentional dead end.
5. **[B5]** §6/§7: add a short paragraph distinguishing `solved` from `done`; specify that
   `/api/next`'s `state` is returned unchanged when `done=true`.
6. **[M1]** §10: once Open Q2 is answered, restate the backend budget total unambiguously.
7. **[M2]** §10: revise core per-module estimates upward (logic ~150–170, search ~110–130, tutor
   ~110–130); add one sentence acknowledging core may land at the high end of 300–450.
8. **[M3]** §10: break the frontend "~390" row into per-file estimates.
9. **[M4]** §10: add a rough phase-by-phase hour table, labeled explicitly as a planning estimate.
10. **[M5]** §5 or §7: add the explicit combined (code × productive × hinted) evidence table.
11. **[M6]** §5: add 2–3 sentences on cache policy (non-`None` only, keyed by state alone).
12. **[M7]** §3 or §7: state the no-duplicate-content invariant explicitly; note it should be
    covered by `test_hint_pair_is_valid_per_core` or a dedicated invariant test.
13. **[M8]** §8: add a "Reversibility" note to each of the 6 decision rows.
14. **[M9]** §8 last row: add the `schemaVersion` mechanism to the localStorage description.
15. **[P1, P2, P3]** §9: add 3 new rows — demo-day (live exploration ballooning clause count),
    schedule (46h/team-size ambiguity), viva readiness (exercise-exhaustion Q&A gap).
16. **[N1]** §5, `diagnose` signature: add "(`existing` includes `a` and `b`)".
17. **[N2]** §11 item 2: extend the proof to cover DOUBLE_CANCEL non-collision explicitly.
18. **[N3]** §5, `distance` signature: add "(0 if the empty clause is already present)".
19. **[N5]** §5/tutor section: add one line on threshold float-comparison (declared a non-issue,
    with why).
20. **[N6]** §8, hints/BKT row: replace "Baker et al." with an unattributed phrase.
21. **[N7]** §6, hint semantics: add "`state` (including `hint_level`) is unchanged when
    `available` is false."

---

## 7. OPEN QUESTIONS (answer changes the design)

1. **Is the ~46-hour effort target a total for the two-person team, or ~46 hours *each*
   (~92 total)?** Changes how much we can responsibly scope into Phases 1–11, and whether the
   10-section report-support kit and E5 pilot are realistic alongside the core build.
2. **Does "backend excluding tests ≤700" include `core/` (300–450) inside it, or is that a
   separate pool on top?** The HLD currently assumes the former and is already at 675/700 with no
   slack (M1).
3. **When the exercise bank is exhausted of unseen exercises in every band, how should repeats be
   chosen** — least-recently-seen (my recommendation), random-but-seeded, or always the lowest
   unseen-adjacent ID? Needed before Phase 4/E4 can be implemented deterministically (B1, B6).
4. **When a student is at exactly 20 clauses and finds one more valid, productive step, should the
   API hard-refuse (400, documented dead end — my recommendation) or should the cap be raised?**
   Needed before Phase 6 (B4).
5. **Confirm: `scripts/difficulty.py` should compute bands in-memory at runtime (no file mutation)
   rather than writing back into `domain.yaml`** (my recommendation, avoids the comment-eating
   YAML bug in B2) — or is there a reason the original write-back design was wanted that I'm
   missing?

---

STOP — awaiting "approved" (or edits to the patch list in §6). On approval: apply only the
approved patches to `docs/HLD.md`, bump to version 1.1, add a Change Log listing each applied
finding ID, re-run passes 3/4/5 to confirm every BLOCKER is closed, and append an
`AI_USAGE_LOG.md` entry. Phase 1 does not start until that re-check is clean.
