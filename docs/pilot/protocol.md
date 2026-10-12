# ProofPilot pilot — 10-minute protocol

Run this after the end-to-end app works (HLD §11, E5) — not before, and not on a half-built
tutor. One facilitator per participant is enough; this is a walk-through, not a proctored exam.

## Timing (10 minutes total)

| Step | Time | What happens |
|---|---|---|
| 1. Consent | 1 min | Participant reads and signs `consent.md`. Assign the next unused ID (`P01`, `P02`, …) from `template.csv`. |
| 2. Pre-test | 2 min | Hand over `pre_test.md`. No tool, no hints, no discussion — work alone. Score it yourself against the answer key at the bottom while they move to step 3. |
| 3. Use the tool | 5 min | Open the app (`npm run dev` + the backend running). If the event log is on for this pilot, type the participant's ID into the app's "Pilot ID" field first — it only appears in pilot mode and otherwise stays hidden. Let them work through 2–3 practice exercises unassisted. Only intervene if the app itself is broken, never to explain a logic step. |
| 4. Post-test + ratings | 2 min | Hand over `post_test.md`. Same rules as the pre-test. Then ask the three 1–5 ratings verbally and record them. |

## The event log (optional, opt-in)

The server can write one line per action to `docs/pilot/logs/pilot.jsonl` — pilot_id, timestamp,
action, result code, hint level, stage, nothing else — but it is OFF unless the facilitator starts
the backend with `PROOFPILOT_PILOT_LOG=1` set. It is a convenience for cross-checking
`codes_seen`, never a replacement for the row in `template.csv`: `analyze_pilot.py` still needs
that row for the test scores and ratings, which the server never sees.

**If this is not set up correctly — or the backend crashes, or there is no time to debug it — skip
it and use the paper tally below instead.** The pilot does not depend on the log working.

## Paper tally sheet (fallback — use if the event log is not running)

One row per participant. Tick a box each time that feedback code appears on screen during step 3.

| Participant | VALID | NO_CLASH | WRONG_RESOLVENT | TAUTOLOGY | DUPLICATE | HINT_1 | HINT_2 | HINT_3 | CLAIM_ACCEPTED | CLAIM_REJECTED |
|---|---|---|---|---|---|---|---|---|---|---|
| P01 | | | | | | | | | | |
| P02 | | | | | | | | | | |
| P03 | | | | | | | | | | |

Transcribe the tallies into `codes_seen` on the matching `template.csv` row (e.g. three `VALID`
ticks and one `HINT_1` tick becomes `VALID;VALID;VALID;HINT_1`) — same column, same script, same
analysis either way.

## What to record, in `template.csv`

One row per participant, appended after the session (never during — it breaks their concentration
and the facilitator should be watching the screen, not typing).

| Column | What it is |
|---|---|
| `participant_id` | `P01`, `P02`, … — assigned at step 1, never a name |
| `pre_test_score` | out of 5, from the `pre_test.md` answer key |
| `post_test_score` | out of 5, from the `post_test.md` answer key |
| `ease_rating` | 1–5, "The tool was easy to use" |
| `clarity_rating` | 1–5, "The feedback messages told me what I did wrong" |
| `confidence_rating` | 1–5, "I feel more confident about resolution proofs now" |
| `exercises_completed` | however many they finished or abandoned in step 3 |
| `codes_seen` | the feedback codes shown on screen during step 3, `;`-separated (e.g. `NO_CLASH;HINT_1;VALID`) — read off the Feedback banner, do not guess |
| `session_minutes` | wall-clock time for the whole session, rounded to the nearest minute |
| `notes` | free text — anything the participant said unprompted, or technical issues. Optional. |

## Rules

- **Never fabricate a row.** A participant who leaves early gets a row with whatever was actually
  observed (even a blank `post_test_score`), never an invented completion.
- **Anonymous only.** No name, no email, nothing that re-identifies the row, per `consent.md`.
- **If the schedule slips**, the pilot is the first thing cut to post-submission (HLD §11, §13.3) —
  do not shorten the consent step or the anonymity rule to save time instead.

## After the last participant

Run `python scripts/analyze_pilot.py` and commit both the populated `template.csv` and the script's
output. It reports counts and medians only — at N≤10 there is no significance test to run, and none
should be added by hand.
