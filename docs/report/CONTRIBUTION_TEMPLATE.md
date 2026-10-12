# Contribution statement — template

This document mixes two kinds of content, and they must not be confused when you fill it in:

- **Fact tables**, pulled directly from the git history. These are not editable opinions — they
  are what the repository actually records.
- **Role tables**, which are *claims the team makes about who did what*. Git commit authorship
  alone cannot establish this (see the note under §2), so every cell there is marked
  **"to be confirmed by students"** and must be filled in and agreed by both of you, not inferred
  by anyone else.

---

## 1. Member × role table

Prefilled with the roles **as stated by the students** in this sprint's planning conversation —
not inferred from commit history. **Every cell still needs the students' own confirmation** before
it goes in the report; treat the prefill as a draft, not a finding.

| Role | CVS Ujwal | Keshav Raj |
|---|---|---|
| Literature review | to be confirmed by students (stated: primary) | to be confirmed by students |
| Methodology & design decisions | to be confirmed by students (stated: primary) | to be confirmed by students |
| Implementation | to be confirmed by students (stated: primary, AI-assisted build) | to be confirmed by students |
| Experimentation | to be confirmed by students (stated: primary) | to be confirmed by students |
| Analysis | to be confirmed by students (stated: primary) | to be confirmed by students |
| Code / design review | to be confirmed by students | to be confirmed by students (stated: primary) |
| Hands-on testing | to be confirmed by students | to be confirmed by students (stated: primary) |
| Held-out paragraphs (human-written) | to be confirmed by students | to be confirmed by students (stated: primary) |
| Pilot material (facilitation, participant recruitment) | to be confirmed by students | to be confirmed by students (stated: primary) |
| Report preparation | to be confirmed by students (stated: primary) | to be confirmed by students |

**Guidance, not a rule:** a 50/50 split in every row is not required and is rarely honest. What
matters to the professor is that the table reflects what actually happened and that both of you
agree it does before submission.

---

## 2. Fact table: commits and files touched, per author

Source: `git shortlog -sne --all`, run 2026-10-12.

| Author | Commits |
|---|---|
| ujwal2311 <ujwal2311.coppisetty@gmail.com> | 70 |

**Only one git author identity exists in this repository as of commit `9d5b0bf`.** Source:
`git log --format="%an <%ae>" | sort -u` → one line. This is a fact about the git history, not a
judgement about who contributed intellectually — Keshav Raj's review, testing, and authoring work
(held-out paragraphs, pilot sessions) does not necessarily appear as a commit under his own name,
and the team should state plainly in the report whether commits were made under one shared
account, or whether Keshav's work genuinely has not yet been committed under his own identity.
**This is a fact for the students to explain, not a conclusion to draw from it.**

### Files touched

Every commit in this repository's history is attributed to the single author above, so a
per-author file-touch breakdown is not meaningful yet (it would just be "all files"). If the team
starts committing under two separate git identities, regenerate this with:

```powershell
git log --author="<name or email>" --name-only --format= | sort -u
```

run once per author, and list the output here as two plain file lists.

### Commit timeline (for context, not for the table above)

Source: `git log --format="%ad|%h|%s" --date=short`.

- First commit: 2026-10-08 (`3030edf`, "Phase 1: scaffold M1 backend, tooling, CI and frozen
  design docs")
- Latest commit: 2026-10-12 (`9d5b0bf`, "Pilot ID persistence + the Edit-facts reset path")
- Span: 5 calendar days, 70 commits.

---

## 3. AI disclosure table

Source: `AI_USAGE_LOG.md` (29 dated entries, one per development phase/sprint block) and the git
commit trailers (`git log --format=%B | grep -c "Co-Authored-By: Claude"` → 58 of 70 commits
carry the trailer).

| Tool | Purpose | Extent | What humans did |
|---|---|---|---|
| Claude Code (Opus 5 / Sonnet 5) | Wrote the design document (`docs/HLD.md`), implemented `backend/src/core`, `backend/src/app`, `backend/src/api`, `backend/src/cli.py`, `frontend/src`, the test suites, and the tooling (`tools/loc.py`, `scripts/*.py`) | 58 of 70 commits carry a `Co-Authored-By: Claude Opus 5` trailer; every `AI_USAGE_LOG.md` entry (29 total) names it as the tool used | Directed every phase via the CLAUDE.md design/engineering rules; made every design decision the log records as "the student decided" (budget, scope, the Facts-confirmation fix, the simulation metric); reviewed and approved each phase gate before proceeding; ran and read every test/lint/CI result before accepting a block as done |
| claude.ai chat (web) | **(a) To be confirmed by students.** Used for ideation, design review, and prompt drafting outside this CLI session, per the task brief — the CLI tool has no record of what happened in a separate chat | not recorded in this repository | to be confirmed by students — list specifically what was discussed/drafted there |
| AI-generated evaluation sets | **(b)** `data/eval/tfl_simple_tier_15.json` and `data/eval/tfl_stress_set_15.json` — both contain a `"source": "AI-generated (Claude)"` field on every item (verified: `python -c "import json; print(set(i['source'] for i in json.load(open('data/eval/tfl_simple_tier_15.json'))))"` → `{'AI-generated (Claude)'}`, same for the stress set) | 15 items each, 30 total; **neither file is yet wired to any evaluation script** (see `FACTS.md` §8) | Students should review every item for topical plausibility before any script consumes them, and must never present these as held-out human-written data — `data/heldout_paragraphs.json` (not yet written) is the human-authored evaluation set and must remain genuinely human-written |
| Pilot forms | **(c)** `docs/pilot/pre_test.md`, `post_test.md`, `consent.md`, `protocol.md`, `template.csv` — drafted by Claude Code in sprint block S8 | 5 files | **To be confirmed by students: which of these were revised, and how, before use in the actual pilot session.** Record any wording changes here. |

### Human-written content (students: fill this in)

The following must be genuinely human-authored — Claude must not write or edit their contents
(CLAUDE.md rule 6, and the pilot/held-out design throughout `docs/HLD.md`):

- [ ] `data/heldout_paragraphs.json` — written by: ________________, date: ________________
- [ ] Pilot session notes / completed `docs/pilot/template.csv` rows — facilitated by:
      ________________, date(s): ________________
- [ ] Report prose (problem statement, objectives, literature review narrative, limitations,
      methodology narrative, analysis, conclusions) — written by: ________________
- [ ] `my_critical_summary` column in `literature_matrix.csv` — written by: ________________
      (currently blank for every row — this is explicitly the students' own critical judgement,
      not a fact Claude can supply)

---

## 4. Checklist before submission

- [ ] §1 role table reviewed and edited by both students (not left as "to be confirmed")
- [ ] §2's single-author fact is explained in the report (shared account, or Keshav's commits
      pending — state which)
- [ ] §3(a) claude.ai chat usage filled in with what was actually discussed there
- [ ] §3(c) pilot form revisions filled in
- [ ] Human-written checklist in §3 fully checked off with names and dates
- [ ] `literature_matrix.csv`'s `my_critical_summary`, `read_by`, and `read` columns filled in for
      every row the team actually read and is citing
