# Demo paragraphs — ready to paste live

**Stamp.** Commit `e0b3aca`, 2026-10-25. Each paragraph below was run through the real, live
`/api/parse` → `confirm_facts` → the hint system's own step suggestions, end to end, via direct
calls to the running backend — not hand-derived. All three report `entailment.verdict == ENTAILED`
and reach `stage == "explain"` (the empty clause) with zero warnings. Resolve-step counts are what
the hint system itself produced, so they match what following Hint 1→2→3 live will show.

These exist so nobody has to hunt for a working paragraph live in front of the professor — paste
one of these three verbatim if the own-argument example being improvised doesn't parse cleanly.

---

## 1. Simple (2 premises, 2 resolve steps)

**Premises:**
> If it rains then the match is cancelled. It rains.

**Conclusion:**
> The match is cancelled.

**Confirmed:** ENTAILED, 2 resolve steps to the empty clause, 5 clauses on the board at the end.
Good for a 30-second "here's the basic loop" demo.

---

## 2. Uses two of tonight's new grammar phrases (3 premises, 2 resolve steps)

**Premises:**
> Provided that the backup battery is low, the system sends an alert. A valid connection is
> necessary for the alert to reach the technician. The backup battery is low.

**Conclusion:**
> The system sends an alert.

**Confirmed:** ENTAILED, 2 resolve steps, 6 clauses at the end. Exercises `"provided that"` (→
`Implies`) and `"is necessary for"` (→ `Implies`, reversed direction) from tonight's grammar
expansion — the necessary-for premise is deliberately irrelevant to the proof itself (shows as
"not needed for this conclusion" on the board), which is also a good moment to point out the
relevance filter live.

---

## 3. Longer chain (4 premises, 4 resolve steps)

**Premises:**
> If the warehouse alarm sounds, then security is notified. If security is notified, then the
> manager is called. If the manager is called, then the incident report is filed. The warehouse
> alarm sounds.

**Conclusion:**
> The incident report is filed.

**Confirmed:** ENTAILED, 4 resolve steps (a clean hypothetical-syllogism chain, A→B→C→D), 9
clauses at the end. Good for showing that the hint ladder and the relevance filter scale past a
single step without the student needing to track more than one new clause at a time.
