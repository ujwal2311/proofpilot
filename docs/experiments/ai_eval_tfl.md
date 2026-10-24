# AI-generated TFL evaluation set -- agreement with ProofPilot's own entailment check

**Date:** 2026-10-25. **Commit:** `9a9b0b4`. **Python:** 3.12.10. **OS:** Windows-11-10.0.26300-SP0.

**Source: AI-generated evaluation set** (`data/eval/tfl_simple_tier_15.json`, `data/eval/tfl_stress_set_15.json`; every item tagged `"source": "AI-generated (Claude)"`). This is not `data/heldout_paragraphs.json`, which stays human-written and unwritten (CLAUDE.md rule 6) and is never read by this script.

## Simple tier: entailment agreement

**15/15 agree** with the item's `expected_follows` (0 not scorable -- parse failure or inconsistent premises).

| id | theme | system verdict | agree |
|---|---|---|---|
| 1 | Greenhouse | True | yes |
| 2 | Tram line | True | yes |
| 3 | Choir | False | yes |
| 4 | Ferry | True | yes |
| 5 | Bakery stall | True | yes |
| 6 | Library desk | False | yes |
| 7 | Stadium | True | yes |
| 8 | Orchard | False | yes |
| 9 | Server room | True | yes |
| 10 | Camp site | False | yes |
| 11 | Quiz team | True | yes |
| 12 | Swimming pool | False | yes |
| 13 | Post office | True | yes |
| 14 | Workshop | False | yes |
| 15 | Cinema | True | yes |

## Stress tier

**15 items**, each a set of harder per-sentence translation drills with no paragraph-level conclusion and no `expected_follows` field -- there is nothing to agree or disagree about here, so none is reported. Per `docs/report/FACTS.md`, neither file has had a human review pass for topical plausibility yet.
