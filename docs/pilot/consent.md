# ProofPilot pilot — consent note

Read this before you start. Ask the facilitator anything before you agree.

**What this is.** A ~10-minute try-out of a propositional-logic proof tutor built for a university
project. You will answer a short pre-test, use the tool on a few exercises, then answer a short
post-test and rate your experience.

**What is recorded.** Your answers to the pre-test and post-test, your 1–5 ratings of the tool,
which feedback codes you encountered while using it, and roughly how long you took. Nothing else
is logged automatically — no keystrokes, no audio, no video.

If the app's own event log is switched on for your session (an opt-in setting the facilitator
turns on, off by default), the server additionally writes one line per action you take: your
participant ID, a timestamp, which action it was (step / hint / claim / confirm), the result code,
the hint level, and the exercise stage. **Never your paragraph text, never a name, never anything
you typed freely** — the log carries codes and counts only, the same six fields every time, and it
is deleted from the machine once `scripts/analyze_pilot.py` has summarised it into counts and
medians.

**Anonymity.** You are assigned a participant ID (e.g. `P01`) on the record sheet
(`docs/pilot/template.csv`) and, if used, in the app's "Pilot ID" field. Your name is never written
next to your answers, ratings, or any logged action, and the facilitator does not keep a separate
list mapping names to IDs after the session.

**What it is used for.** Aggregate counts and medians across all participants go into the
project's evaluation report, alongside the exact script that computed them
(`scripts/analyze_pilot.py`) and the commit it was run against. With fewer than ten participants,
no claim of statistical significance is made — only what was observed, honestly reported.

**Participation is voluntary.** You can stop at any point, skip any question, and ask that your
row be deleted from the record sheet before analysis — just tell the facilitator. There is no
penalty for not participating or for stopping partway through.

**Who to contact.** The two students running this project, listed in the repository's README.

---

I have read the above and agree to take part.

Participant initials: ______________   Date: ______________
