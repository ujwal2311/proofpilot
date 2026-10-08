# CLAUDE.md — ProofPilot rules and constraints

**Design: see `docs/HLD.md` v2.3 — APPROVED AND FROZEN (2026-10-08).** Any design change requires
an explicit change request from the student; never alter the design unilaterally. That document is
the single source of truth for architecture,
grammar, algorithms, data model, API contract, budgets, milestones and test names. This file holds
rules and constraints only — if a design detail appears here, it is a duplication bug; delete it
here and keep the HLD.

---

# ACADEMIC INTEGRITY (overrides everything else)

The professor prohibits AI-generated content submitted as original academic work; permitted AI use
must be disclosed. Therefore:

1. Claude MAY write: code, tests, scripts, config, README, `docs/HLD.md`,
   `docs/misconceptions.md`, experiment outputs produced by running code, templates, outlines,
   checklists, guiding questions.
2. Claude MUST NOT write report prose — no drafted paragraphs for problem statement, objectives,
   literature review, limitations, methodology narrative, analysis or conclusions. If asked,
   refuse briefly and offer an outline, guiding questions, or a review.
3. REVIEW MODE: when the student pastes their own text and says "review", list factual errors,
   unsupported claims, missing citations, unclear explanations, and contradictions with code or
   results — each with a line reference. Do not rewrite their text. Do not supply replacement
   sentences.
4. References: never invent a paper, author, year, DOI or URL. A reference enters `references.md`
   only after its DOI or publisher page has been fetched and the title, authors and year
   confirmed. Otherwise mark UNVERIFIED and leave it out.
5. `AI_USAGE_LOG.md` is kept at the repo root. After every phase append: date, phase, tool
   ("Claude Code", model name), files created or modified, what the student changed by hand (ask),
   and the purpose. Factual only. No estimated percentages.
6. `data/heldout_paragraphs.json` is written by humans (the student and classmates) after the
   parser is frozen. Claude must never author or edit its contents, and it is never used for
   tuning.

# HARD CONSTRAINTS

- Backend: Python 3.11+, FastAPI, Pydantic. Frontend: React + Vite, JavaScript, hooks, plain CSS.
  No Redux, no component library, no Next.js, no Streamlit, Gradio or notebooks.
- All logic lives in `backend/src/core`: pure Python, dataclasses, **no fastapi / pydantic / web
  imports**. The API is a thin 4-endpoint layer. React renders and posts — no logic.
- Only syllabus techniques: controlled-grammar parsing, truth tables, resolution, BFS, BKT.
  No ML, no LLMs, no RL, no NLP library, no database, no Docker, no auth, no WebSockets, no cloud.
- DO NOT BUILD: A*, set-of-support (stretch only), first-order logic or unification, accounts, a
  database, a teacher dashboard, LLM features, Docker, free-form NLP.
- Budgets (measured and reported at **every** gate), per `docs/HLD.md` v2.3 §13.4 — all five are
  currently met, with only 30–45 lines of headroom each:
  **core ≤975** · **api + cli ≤350** · **scripts ≤250** · **frontend ≤700** ·
  **77.00 person-hours** for the 2-person team (≈38.5 h each; contingency 75.00 by moving the
  pilot post-submission).
  **Exceeding a budget means STOP and justify. Never silently absorb it, and never re-base a cap
  onto the actual.**
- Both members must be able to explain every module. Joint walkthroughs are budgeted (§13.3), and
  `docs/HLD.md` §17.11 holds the three-sentence explanation of each module.

# NON-NEGOTIABLE DESIGN PRINCIPLES

1. **No hardcoding.** No exercise-specific code, no per-question or per-topic word lists, no
   special-casing any example. Every exercise is data (paragraph + conclusion) through one general
   pipeline. Enforced by `test_no_exercise_words_in_core`.
2. **Never guess.** An ambiguous or unsupported sentence returns a named error identifying the
   sentence with one rephrasing hint. Two facts that might be the same are never merged silently —
   the user decides.
3. **Verifiable.** Every judgment (translation correct, step valid, conclusion follows) is decided
   by truth table or the resolution rule. No LLM, no ML, no NLP libraries.
4. **Simple.** Prefer the simplest correct design. No abstraction without a second real use.
5. **Honest.** Never claim to understand free-form English. State the supported language precisely
   and keep the limitations list accurate.

# ENGINEERING RULES

1. Contract first: before each module state its purpose, signatures, invariants, edge cases and
   tests. Then write the tests. Then the implementation.
2. Never add more than ~150 lines of non-test code before running pytest. Show the output.
3. No speculative generality, dead code, TODO stubs or commented-out code.
4. Determinism: never depend on set or dict iteration order. Sort canonically. Seed every random
   generator from `core/config.py`.
5. Never swallow exceptions. Validate at the boundaries.
6. If a test fails twice with the same approach, stop, state the root cause, then fix it. Never
   weaken or delete a test to make it pass.
7. Dependencies: runtime = fastapi, uvicorn, pydantic, pyyaml (`requirements.txt`);
   dev = pytest, httpx, matplotlib, ruff (`requirements-dev.txt`); frontend = react, react-dom,
   vite + its React plugin. Ask before adding anything, and put it in the right file.
8. Windows-friendly: PowerShell commands in the README, `pathlib` for paths, Makefile optional.
9. Type hints, short docstrings, comments that explain WHY.
10. Never invent results. Every number in docs comes from a script run, stamped with date and git
    commit hash. Planning estimates must be labelled as estimates, never as results.
11. Every numeric limit and seed lives in `core/config.py` and nowhere else.
12. Git: small commits with meaningful messages. Push after every approved gate. Never force-push.
    Never commit `.env`, virtual environments or `node_modules`.

# GATES

At the end of every phase, STOP and print a PHASE REPORT: files and line counts · pytest summary ·
decisions made and alternatives rejected · bugs, risks and gaps found and how handled · 4–6 plain
sentences for the viva · the `AI_USAGE_LOG.md` entry being added · proposed commit message.
Wait for "approved", then commit and push.

`docs/HLD.md` §15 Open Questions are resolved and v2.3 is frozen. Implementation proceeds
milestone by milestone: **M1 first and complete**, M2 only after M1 ships.
