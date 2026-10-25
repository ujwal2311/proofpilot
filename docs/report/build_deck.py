"""Builds docs/report/ProofPilot_Progress_Report.pptx from the committed report kit.

Run with the throwaway venv's python-pptx (NOT a project dependency):

    /tmp/pptx_venv/Scripts/python.exe docs/report/build_deck.py

Every number on these slides is copied from FACTS.md / PROGRESS.md / references.md /
literature_matrix.csv / CONTRIBUTION_TEMPLATE.md -- this script does not compute or invent any
of them. Where the kit deliberately left a cell blank for the students
(my_critical_summary, every role-table cell, every AI-disclosure "extent" cell), that placeholder
text is kept verbatim rather than inferred.

Deck rules: 16:9, white background, one accent colour (#1F4E79), Calibri, text/tables/plain
rectangles only -- zero images, icons, charts, gradients, animations.
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x1A, 0x1A, 0x1A)
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)
FONT = "Calibri"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

REPO_URL = "https://github.com/ujwal2311/proofpilot.git"
COMMIT = "e0b3aca"  # local working commit this deck is built from -- pushed, CI-verified green

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


def new_slide():
    return prs.slides.add_slide(BLANK)


def set_background_white(slide):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = WHITE


_DEFAULT_LINE_WIDTH = Pt(1)


def add_rect(slide, left, top, width, height, fill=None, line=None, line_width=_DEFAULT_LINE_WIDTH):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.shadow.inherit = False
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = line_width
    return shape


def add_textbox(slide, left, top, width, height, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(2)
    tf.margin_bottom = Pt(2)
    return box, tf


def set_run(run, text, size=14, bold=False, italic=False, color=BLACK, font=FONT):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font


def add_footer(slide, number):
    box, tf = add_textbox(slide, Inches(0.3), Inches(7.15), Inches(4), Inches(0.3))
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, f"ProofPilot | {number}", size=10, color=RGBColor(0x66, 0x66, 0x66))


def add_title_bar(slide, title_text, subtitle_text=None):
    add_rect(slide, 0, 0, SLIDE_W, Inches(1.0), fill=ACCENT)
    box, tf = add_textbox(slide, Inches(0.4), Inches(0.08), Inches(12.5), Inches(0.6))
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, title_text, size=26, bold=True, color=WHITE)
    if subtitle_text:
        box2, tf2 = add_textbox(slide, Inches(0.4), Inches(0.62), Inches(12.5), Inches(0.35))
        p2 = tf2.paragraphs[0]
        r2 = p2.add_run()
        set_run(r2, subtitle_text, size=13, color=WHITE)


def make_table(
    slide, left, top, width, height, rows, cols, col_widths=None, font_size=12, header=True
):
    gtable = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = gtable.table
    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = w
    for r in range(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            cell.margin_left = Pt(4)
            cell.margin_right = Pt(4)
            cell.margin_top = Pt(2)
            cell.margin_bottom = Pt(2)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if header and r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ACCENT
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT_GREY
    return table


def fill_cell(
    table, r, c, text, size=12, bold=False, color=None, align=PP_ALIGN.LEFT, italic=False
):
    cell = table.cell(r, c)
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    header_color = WHITE if (bold and color is None) else (color or BLACK)
    set_run(run, text, size=size, bold=bold, color=header_color, italic=italic)


# ============================================================ SLIDE 1 -- Title
s = new_slide()
set_background_white(s)
add_rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=None, line=None)
add_rect(s, 0, Inches(2.6), SLIDE_W, Inches(2.2), fill=ACCENT)

box, tf = add_textbox(s, Inches(1.0), Inches(2.85), Inches(11.3), Inches(1.0))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "ProofPilot", size=44, bold=True, color=WHITE)

box, tf = add_textbox(s, Inches(1.0), Inches(3.6), Inches(11.3), Inches(0.5))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Step-level formative feedback for propositional logic proofs", size=18, color=WHITE)

box, tf = add_textbox(s, Inches(1.0), Inches(5.1), Inches(11.3), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Project progress report | Artificial Intelligence (Theory)", size=16, bold=True)

box, tf = add_textbox(s, Inches(1.0), Inches(5.55), Inches(11.3), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Team: CVS Ujwal, Keshav Raj", size=14)

box, tf = add_textbox(s, Inches(1.0), Inches(6.0), Inches(11.3), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, f"Repository: {REPO_URL}", size=12, color=RGBColor(0x44, 0x44, 0x44))

box, tf = add_textbox(s, Inches(1.0), Inches(6.35), Inches(11.3), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    f"Report built from commit {COMMIT} (pushed, CI-verified green -- see slide 6)",
    size=12,
    color=RGBColor(0x44, 0x44, 0x44),
)
add_footer(s, 1)


# =========================================== SLIDE 2 -- Problem Statement & Objectives
s = new_slide()
set_background_white(s)
add_title_bar(s, "1-2. Problem Statement and Objectives")

col_w = Inches(6.1)
col_h = Inches(5.8)
left1, left2 = Inches(0.35), Inches(6.75)
top = Inches(1.25)

for left, heading in ((left1, "Problem Statement"), (left2, "Objectives")):
    add_rect(s, left, top, col_w, col_h, fill=LIGHT_GREY, line=ACCENT, line_width=Pt(1.5))
    box, tf = add_textbox(
        s, left + Inches(0.15), top + Inches(0.08), col_w - Inches(0.3), Inches(0.3)
    )
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(
        r,
        "AI-drafted -- review and rewrite in your own words",
        size=10,
        italic=True,
        color=RGBColor(0x60, 0x60, 0x60),
    )
    box, tf = add_textbox(
        s, left + Inches(0.15), top + Inches(0.4), col_w - Inches(0.3), Inches(0.3)
    )
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, heading, size=16, bold=True, color=ACCENT)

PROBLEM_TEXT = (
    "When a student works through a propositional-logic proof -- turning an English argument "
    "into premises, converting them to clauses, and resolving step by step -- the two places "
    "they actually go wrong are translation (misreading “unless” or “only if”) "
    "and the proof steps themselves (picking an irrelevant clause, or claiming a conclusion that "
    "doesn’t follow). In a classroom, a teacher can mark the final answer right or wrong, but "
    "checking every intermediate step for each student isn’t possible at scale, so a student "
    "who makes a mistake early often doesn’t find out until the grade comes back -- by which "
    "point the specific misunderstanding is gone. ProofPilot addresses this by giving step-level "
    "feedback as the student works: it reads a plain-English argument, builds the proof with the "
    "student rather than for them, and tracks which skills (translation, clause selection, "
    "relevance) the student has and hasn’t mastered, adjusting what it asks next. This "
    "matters because formative feedback -- feedback given during the work, not after it -- is "
    "what lets a student correct a misunderstanding before it hardens into a habit."
)

box, tf = add_textbox(
    s, left1 + Inches(0.15), top + Inches(0.8), col_w - Inches(0.3), col_h - Inches(0.95)
)
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, PROBLEM_TEXT, size=12.5)

OBJECTIVES = [
    "Parse a plain-English argument of arbitrary length into logical facts without hardcoded "
    "vocabulary, refusing (by name, with a rephrasing hint) any sentence it cannot confidently "
    "translate, rather than guessing.",
    "Verify, using resolution refutation cross-checked against truth-table entailment, whether a "
    "stated conclusion actually follows from the student’s premises -- correctly, on a "
    "benchmark of randomly generated problems.",
    "Generate a step-level hint at each stage of the proof, using breadth-first search over the "
    "remaining clauses, within a bounded and deterministic search budget.",
    "Track per-skill mastery with Bayesian Knowledge Tracing and use it to decide, after each "
    "answer, whether to keep practicing or move on -- measurably reducing how often a simulated "
    "learner is released before mastery, compared to a fixed-length baseline.",
]
box, tf = add_textbox(
    s, left2 + Inches(0.15), top + Inches(0.8), col_w - Inches(0.3), col_h - Inches(0.95)
)
tf.word_wrap = True
for i, obj in enumerate(OBJECTIVES):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(8)
    r = p.add_run()
    set_run(r, f"• {obj}", size=12)

add_footer(s, 2)


# =========================================== SLIDE 3 -- Literature Review & Limitations
s = new_slide()
set_background_white(s)
add_title_bar(s, "3-4. Literature Review and Limitations")

LIT_ROWS = [
    (
        "Knowledge tracing & student modeling",
        "Corbett & Anderson (1995); Baker et al. (2008); Pardos & Heffernan (2010); Pavlik et al. "
        "(2009); Piech et al. (2015); Khajah et al. (2016); Pelánek (2017); Bull & Kay (2007)",
        "Classical BKT, extended with contextual/individual parameters, matches deep-learning "
        "tracers on the benchmarks tested.",
    ),
    (
        "ITS & tutoring effectiveness",
        "VanLehn (2006, 2011); Kulik & Fletcher (2016); Ma et al. (2014); Bloom (1984)",
        "ITS approach human-tutor effect sizes (~0.7-0.8 SD); exact gains vary by outcome-measure "
        "type.",
    ),
    (
        "Feedback & formative assessment",
        "Black & Wiliam (1998); Hattie & Timperley (2007); Shute (2008); Brown & Burton (1978)",
        "Specific, timely, non-evaluative feedback that names the error "
        "outperforms a single grade.",
    ),
    (
        "Logic-proof tutoring & hint generation",
        "Robinson (1965); Barnes & Stamper (2008); Stamper et al. (2013)",
        "Resolution is the proof method; data-driven/MDP-based hints measurably help students "
        "persist through logic-proof tutors.",
    ),
    (
        "Help-seeking & misuse detection",
        "Aleven et al. (2006) × 2 papers found; Baker et al. (2004)",
        "Student help-seeking and gaming behaviour can be modeled and detected from interaction "
        "logs.",
    ),
    (
        "Theoretical background",
        "Doignon & Falmagne (1999); Russell & Norvig (2020)",
        "Formal knowledge-space theory and standard course material (logic, search) underpin the "
        "design.",
    ),
]

table = make_table(
    s,
    Inches(0.3),
    Inches(1.2),
    Inches(12.7),
    Inches(4.9),
    len(LIT_ROWS) + 1,
    4,
    col_widths=[Inches(2.5), Inches(4.3), Inches(4.1), Inches(1.8)],
    font_size=11,
)
headers = ["Theme", "Papers (verified citation)", "Key finding", "Gap"]
for c, h in enumerate(headers):
    fill_cell(table, 0, c, h, size=12, bold=True)
for i, (theme, papers, finding) in enumerate(LIT_ROWS, start=1):
    fill_cell(table, i, 0, theme, size=11, bold=True, color=ACCENT)
    fill_cell(table, i, 1, papers, size=10.5)
    fill_cell(table, i, 2, finding, size=10.5)
    fill_cell(
        table, i, 3, "[STUDENTS WRITE]", size=10.5, italic=True, color=RGBColor(0x70, 0x70, 0x70)
    )

box, tf = add_textbox(s, Inches(0.3), Inches(6.2), Inches(12.7), Inches(0.85))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    "23 of 24 seed citations verified, 1 ambiguous (Aleven et al. 2006, two papers "
    "found, pick one). 25-30 required — more still needed.",
    size=12,
    italic=True,
    color=RGBColor(0x40, 0x40, 0x40),
)

add_footer(s, 3)


# ============================================================ SLIDE 4 -- Methodology: Architecture
s = new_slide()
set_background_white(s)
add_title_bar(s, "5. Methodology: Architecture and Workflow")

PIPELINE = ["parse", "facts", "consistency", "entailment", "relevance", "proof"]
pw = Inches(1.95)
ph = Inches(0.75)
gap = Inches(0.15)
start_x = Inches(0.35)
py = Inches(1.3)
for i, stage in enumerate(PIPELINE):
    x = start_x + i * (pw + gap)
    add_rect(
        s,
        x,
        py,
        pw,
        ph,
        fill=ACCENT if i in (2, 3) else LIGHT_GREY,
        line=ACCENT,
        line_width=Pt(1.25),
    )
    box, tf = add_textbox(s, x, py, pw, ph, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, stage, size=13, bold=True, color=WHITE if i in (2, 3) else ACCENT)
    if i < len(PIPELINE) - 1:
        box2, tf2 = add_textbox(s, x + pw, py, gap, ph, anchor=MSO_ANCHOR.MIDDLE)
        p2 = tf2.paragraphs[0]
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run()
        set_run(r2, "→", size=16, bold=True, color=ACCENT)

box, tf = add_textbox(s, Inches(0.35), Inches(2.18), Inches(12.6), Inches(0.75))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    'Above: the 6-step INTERNAL pipeline (docs/HLD.md §7). Not the only "stage" count -- '
    "three numbers, kept separate rather than flattened to one (FACTS.md §9):",
    size=11,
    italic=True,
    color=RGBColor(0x60, 0x60, 0x60),
)
p2 = tf.add_paragraph()
r2 = p2.add_run()
set_run(
    r2,
    "3 UI screens  •  5-value state machine (read/facts/translate/prove/explain -- "
    "translate now universal, HLD v2.12)  •  6-step internal pipeline (above)",
    size=11,
    bold=True,
    color=ACCENT,
)

ARCH_BOXES = [
    ("React frontend", "Render, post actions,\npersist to localStorage"),
    ("FastAPI (4 endpoints)", "Stateless HTTP adapter:\nparse body, call app, return JSON"),
    ("app/ (shared edge)", "load+validate, prepare,\nrender, mint clause ids"),
    ("core/ (15 modules)", "Pure Python, zero web\nimports, 6-stage pipeline"),
]
bw = Inches(2.95)
bh = Inches(1.3)
bgap = Inches(0.2)
bx = Inches(0.35)
by = Inches(3.05)
for i, (name, desc) in enumerate(ARCH_BOXES):
    x = bx + i * (bw + bgap)
    add_rect(s, x, by, bw, bh, fill=WHITE, line=ACCENT, line_width=Pt(1.5))
    box, tf = add_textbox(s, x + Inches(0.1), by + Inches(0.08), bw - Inches(0.2), Inches(0.35))
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, name, size=13, bold=True, color=ACCENT)
    box2, tf2 = add_textbox(
        s, x + Inches(0.1), by + Inches(0.45), bw - Inches(0.2), bh - Inches(0.55)
    )
    for j, line in enumerate(desc.split("\n")):
        p2 = tf2.paragraphs[0] if j == 0 else tf2.add_paragraph()
        r2 = p2.add_run()
        set_run(r2, line, size=11)
    if i < len(ARCH_BOXES) - 1:
        box3, tf3 = add_textbox(
            s, x + bw, by + Inches(0.4), bgap, Inches(0.5), anchor=MSO_ANCHOR.MIDDLE
        )
        p3 = tf3.paragraphs[0]
        p3.alignment = PP_ALIGN.CENTER
        r3 = p3.add_run()
        set_run(r3, "→", size=16, bold=True, color=ACCENT)

box, tf = add_textbox(s, Inches(0.35), Inches(4.55), Inches(12.6), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Implementation strategy (FACTS.md §9)", size=14, bold=True, color=ACCENT)

STRATEGY = [
    "core/ imports nothing outside the standard library -- unit-testable from literals.",
    "app/ is the only layer allowed to read a data file, validated at startup.",
    "api/ and cli.py are thin adapters: zero logic, zero wording of their own.",
    "frontend/src reads state.stage directly -- no client-side copy of the stage.",
]
box, tf = add_textbox(s, Inches(0.35), Inches(4.95), Inches(6.1), Inches(2.1))
for i, line in enumerate(STRATEGY):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(8)
    r = p.add_run()
    set_run(r, f"• {line}", size=12)

box, tf = add_textbox(s, Inches(6.75), Inches(4.55), Inches(6.2), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Added 2026-10-25 (FACTS.md §2)", size=14, bold=True, color=ACCENT)

ADDED_TONIGHT = [
    "8 new grammar phrases (HLD v2.13): necessary/sufficient-for, implies, not-both, "
    "whenever, provided/given-that, otherwise.",
    "Prove screen: symbol legend + per-clause plain-English rendering (clause_english).",
    "All 3 stage tabs independently browsable -- view-only, never calls the API.",
    "A Back button beside the tabs, same view-only navigation.",
]
box, tf = add_textbox(s, Inches(6.75), Inches(4.95), Inches(6.2), Inches(2.1))
for i, line in enumerate(ADDED_TONIGHT):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(8)
    r = p.add_run()
    set_run(r, f"• {line}", size=12)

add_footer(s, 4)


# ========================================= SLIDE 5 -- Methodology: Algorithms & Syllabus
s = new_slide()
set_background_white(s)
add_title_bar(s, "5. Methodology: Algorithms and Syllabus Mapping")

ALGO_ROWS = [
    (
        "Parsing",
        "Controlled-grammar keyword scan → AST → clauses (textbook 3-step CNF algorithm)",
        "core/english.py, core/cnf.py",
    ),
    (
        "Entailment",
        "Truth-table enumeration, cross-checked against resolution (940/940 agreement)",
        "core/entail.py",
    ),
    (
        "Proof search",
        "Exact breadth-first search over clause sets, bounded work budget, rule-based fallback",
        "core/search.py",
    ),
    (
        "Mastery tracking",
        "Single-skill Bayesian Knowledge Tracing, 3 skills (CLASH, RESOLVE, STRATEGY)",
        "core/bkt.py",
    ),
]
table = make_table(
    s,
    Inches(0.3),
    Inches(1.2),
    Inches(12.7),
    Inches(2.6),
    len(ALGO_ROWS) + 1,
    3,
    col_widths=[Inches(2.3), Inches(7.4), Inches(3.0)],
    font_size=12,
)
for c, h in enumerate(["Component", "Algorithm", "Module(s)"]):
    fill_cell(table, 0, c, h, size=13, bold=True)
for i, (comp, algo, mod) in enumerate(ALGO_ROWS, start=1):
    fill_cell(table, i, 0, comp, size=12, bold=True, color=ACCENT)
    fill_cell(table, i, 1, algo, size=11.5)
    fill_cell(table, i, 2, mod, size=11.5)

box, tf = add_textbox(s, Inches(0.3), Inches(4.05), Inches(12.6), Inches(0.4))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "Syllabus-unit mapping (README.md, verbatim)", size=14, bold=True, color=ACCENT)

SYL_ROWS = [
    ("Unit 2 — Search", "Breadth-first search", "core/search.py"),
    ("Unit 4 — Logic", "Resolution, refutation", "core/logic.py, core/cnf.py"),
    ("Unit 5 — Uncertainty", "Bayes' rule, Bayesian Knowledge Tracing", "core/bkt.py"),
]
table2 = make_table(
    s,
    Inches(0.3),
    Inches(4.5),
    Inches(12.7),
    Inches(2.0),
    len(SYL_ROWS) + 1,
    3,
    col_widths=[Inches(3.2), Inches(5.5), Inches(4.0)],
    font_size=13,
)
for c, h in enumerate(["Syllabus unit", "Topic", "Where implemented"]):
    fill_cell(table2, 0, c, h, size=13, bold=True)
for i, (unit, topic, mod) in enumerate(SYL_ROWS, start=1):
    fill_cell(table2, i, 0, unit, size=12.5, bold=True, color=ACCENT)
    fill_cell(table2, i, 1, topic, size=12.5)
    fill_cell(table2, i, 2, mod, size=12.5)

add_footer(s, 5)


# =========================================== SLIDE 6 -- Code Repository & Build Record
s = new_slide()
set_background_white(s)
add_title_bar(s, "6. Code Repository and Build Record")

REPO_ROWS = [
    ("Repository URL", REPO_URL),
    ("Licence", "MIT"),
    ("Total commits", "95 (git log --format=%H | wc -l)"),
    (
        "Latest commit (this deck)",
        COMMIT + " -- pushed, CI-verified green",
    ),
    (
        "Push status",
        "Pushed. origin/main is at " + COMMIT + "; CI confirmed green for this exact commit.",
    ),
    (
        "CI status (last 20 pushes)",
        "17/20 succeeded; 3 consecutive failures on 2026-10-23 (missing data/eval/*.json in "
        "git), fixed 2026-10-24 -- every push since, including all of tonight's, is green "
        "(gh run list --branch main --limit 20)",
    ),
    ("progress-v1 tag", "points at fef68ba, 2026-10-24/25 (git tag --list progress-v1)"),
    ("AI_USAGE_LOG.md entries", "37 dated entries, one per development phase/sprint block/gate"),
    (
        "Commits with Co-Authored-By: Claude",
        '81 of 95 (git log --format=%B | grep -c "Co-Authored-By")',
    ),
]
table = make_table(
    s,
    Inches(0.3),
    Inches(1.3),
    Inches(12.7),
    Inches(4.55),
    len(REPO_ROWS) + 1,
    2,
    col_widths=[Inches(3.9), Inches(8.8)],
    font_size=12,
    header=False,
)
fill_cell(table, 0, 0, "Fact", size=12, bold=True, color=WHITE)
table.cell(0, 0).fill.solid()
table.cell(0, 0).fill.fore_color.rgb = ACCENT
fill_cell(table, 0, 1, "Value", size=12, bold=True, color=WHITE)
table.cell(0, 1).fill.solid()
table.cell(0, 1).fill.fore_color.rgb = ACCENT
for i, (fact, value) in enumerate(REPO_ROWS, start=1):
    fill_cell(table, i, 0, fact, size=11, bold=True, color=ACCENT)
    fill_cell(table, i, 1, value, size=10.5)

box, tf = add_textbox(s, Inches(0.3), Inches(6.0), Inches(12.7), Inches(0.9))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    "Every figure above is sourced to the exact command that produced it "
    "(docs/report/FACTS.md §1) — re-run any of them to re-check.",
    size=12,
    italic=True,
    color=RGBColor(0x50, 0x50, 0x50),
)

add_footer(s, 6)


# ============================================================ SLIDE 7 -- Simulation
s = new_slide()
set_background_white(s)
add_title_bar(s, "7. Experiments: Stopping-Rule Simulation")

SIM_ROWS = [
    ("baseline (fixed-N)", "21.00", "8.00", "4.45"),
    ("adaptive-matched", "2.60", "7.57", "2.67"),
    ("adaptive-mismatched", "4.80", "11.51", "3.78"),
]
table = make_table(
    s,
    Inches(0.3),
    Inches(1.25),
    Inches(12.7),
    Inches(2.2),
    len(SIM_ROWS) + 1,
    4,
    col_widths=[Inches(3.2), Inches(3.3), Inches(3.0), Inches(3.2)],
    font_size=14,
)
for c, h in enumerate(["Policy", "Premature-release %", "Mean exercises", "Mean over-practice"]):
    fill_cell(table, 0, c, h, size=13, bold=True)
for i, row in enumerate(SIM_ROWS, start=1):
    for c, val in enumerate(row):
        fill_cell(table, i, c, val, size=13, bold=(c == 0), color=ACCENT if c == 0 else None)

box, tf = add_textbox(s, Inches(0.3), Inches(3.65), Inches(12.7), Inches(0.35))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    "Seed 20261012, N=500 simulated learners per arm (python scripts/run_experiments.py --write)",
    size=12,
    bold=True,
)

CAVEATS = [
    "The adaptive-mismatched arm uses MORE exercises than the baseline (11.51 vs 8.00) and is "
    "NOT budget-matched to it. The correct claim: it still keeps premature release low (4.8%) "
    "at roughly 50% more practice than the matched arm — not that it beats the baseline at "
    "an equal budget.",
    "“The simulation tests only the stopping rule under the model’s own assumptions” "
    "(HLD §14 item 9, verbatim) — not evidence that students learn more.",
    "One BKT-tracked skill is simulated per learner, not three, because the three real skills "
    "update independently under identical dynamics.",
    "The mismatched arm's “true” slip/transit parameters are a labelled design decision, "
    "not a fit to real data.",
]
box, tf = add_textbox(s, Inches(0.3), Inches(4.1), Inches(12.7), Inches(2.8))
for i, c in enumerate(CAVEATS):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(8)
    r = p.add_run()
    set_run(r, f"• {c}", size=12)

add_footer(s, 7)


# =========================================== SLIDE 8 -- Experimental Analysis & Progress
s = new_slide()
set_background_white(s)
add_title_bar(s, "8. Experimental Analysis and Current Progress")

ANALYSIS_ROWS = [
    (
        "Tests",
        "864/865 passed (1 skipped by default: 400-case slow sweep, needs "
        "PROOFPILOT_SLOW=1, passes with nothing skipped in CI's dedicated slow job). Both "
        "PYTHONHASHSEED=0 and 4242 green.",
    ),
    (
        "Differential testing",
        "940/940 agreement between truth-table entailment and resolution (100%). Unchanged "
        "since v2.9 -- regression-checked tonight, still 7/7 passing.",
    ),
    (
        "Mutation testing",
        "82/82 (Phase 6a core modules, 2026-10-11, 416-test suite) PLUS a separate "
        "43/43 (every module built since, run for the first time: session.py, tutor.py, "
        "config.py, formula.py, translation.py, narrate.py -- 842-test suite, 2026-10-25). "
        "Two different scopes at two different suite sizes -- do not add them.",
    ),
    (
        "Search latency",
        "Deepest bank proof (5 steps): 12.7 ms. Deepest budget-answered proof "
        "(7 steps): 691 ms. 8+ steps fall back to a rule-based hint. Unchanged since v2.9 A3.",
    ),
    (
        "Evaluation sets",
        "data/eval/*.json now committed to git and wired (scripts/ai_eval_tfl.py): the "
        "15-item simple tier agrees 15/15 with ProofPilot's own entailment check. The 15-item "
        "stress tier has a different schema (no conclusion/expected_follows) -- counted, not "
        "scored.",
    ),
    ("Pilot (E5)", "Not run. Tooling ready; template.csv has a header row only."),
    (
        "M2 (translation coach)",
        "Core modules built (formula.py, translation.py, narrate.py, 6/6/3 mutants caught) "
        "plus the evidence-mapping wiring (tutor.translate_trigger, session.record_translation) "
        "and a design change making Translate universal (HLD v2.12). The real check -- a "
        "reference-formula renderer, diagnosis messages, the API handler, the frontend step -- "
        "is DEFERRED by explicit decision, not an oversight: it would cross a core budget cap "
        "and worsen an already-over-ceiling bucket (HLD v2.12 change log has the numbers). "
        "Every exercise today auto-skips Translate, restoring exact pre-change behaviour.",
    ),
    ("Analysis of results", "[STUDENTS WRITE: your interpretation]"),
    (
        "Next",
        "The M2 Translate check (deferred above, budget decision needed) → the pilot session "
        "→ data/heldout_paragraphs.json (human-written, post-freeze) → report prose.",
    ),
]
table = make_table(
    s,
    Inches(0.3),
    Inches(1.2),
    Inches(12.7),
    Inches(5.9),
    len(ANALYSIS_ROWS) + 1,
    2,
    col_widths=[Inches(2.6), Inches(10.1)],
    font_size=11,
    header=False,
)
fill_cell(table, 0, 0, "Item", size=13, bold=True, color=WHITE)
table.cell(0, 0).fill.solid()
table.cell(0, 0).fill.fore_color.rgb = ACCENT
fill_cell(table, 0, 1, "Status", size=13, bold=True, color=WHITE)
table.cell(0, 1).fill.solid()
table.cell(0, 1).fill.fore_color.rgb = ACCENT
for i, (item, status) in enumerate(ANALYSIS_ROWS, start=1):
    italic = item == "Analysis of results"
    fill_cell(table, i, 0, item, size=11.5, bold=True, color=ACCENT)
    fill_cell(
        table,
        i,
        1,
        status,
        size=10.5,
        italic=italic,
        color=RGBColor(0x70, 0x70, 0x70) if italic else None,
    )

add_footer(s, 8)


# ============================================================ SLIDE 9 -- References
s = new_slide()
set_background_white(s)
add_title_bar(s, "9. References (APA)")

REFERENCES = [
    "Aleven, V., McLaren, B., Roll, I., & Koedinger, K. (2006). Toward meta-cognitive tutoring: "
    "A model of help seeking with a cognitive tutor. IJAIED, 16(2), 101–128.",
    "Aleven, V., McLaren, B. M., Sewall, J., & Koedinger, K. R. (2006). The Cognitive Tutor "
    "Authoring Tools (CTAT): Preliminary evaluation of efficiency gains. ITS 2008, 61–70.",
    "Baker, R. S., Corbett, A. T., & Koedinger, K. R. (2004). Detecting student misuse of "
    "intelligent tutoring systems. ITS 2004, 531–540.",
    "Baker, R. S. J. d., Corbett, A. T., & Aleven, V. (2008). More accurate student modeling "
    "through contextual estimation of slip and guess probabilities in BKT. ITS 2008, 406–415.",
    "Barnes, T., & Stamper, J. (2008). Toward automatic hint generation for logic proof "
    "tutoring using historical student data. ITS 2008, 373–382.",
    "Black, P., & Wiliam, D. (1998). Assessment and classroom learning. Assessment in "
    "Education, 5(1), 7–74.",
    "Bloom, B. S. (1984). The 2 sigma problem. Educational Researcher, 13(6), 4–16.",
    "Brown, J. S., & Burton, R. R. (1978). Diagnostic models for procedural bugs in basic "
    "mathematical skills. Cognitive Science, 2(2), 155–192.",
    "Bull, S., & Kay, J. (2007). Student models that invite the learner in: The SMILI "
    "framework. IJAIED, 17(2), 89–120.",
    "Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of "
    "procedural knowledge. UMUAI, 4(4), 253–278.",
    "Doignon, J.-P., & Falmagne, J.-C. (1999). Knowledge spaces. Springer.",
    "Hattie, J., & Timperley, H. (2007). The power of feedback. Review of Educational "
    "Research, 77(1), 81–112.",
    "Khajah, M., Lindsey, R. V., & Mozer, M. C. (2016). How deep is knowledge tracing? EDM 2016.",
    "Kulik, J. A., & Fletcher, J. D. (2016). Effectiveness of intelligent tutoring systems. "
    "Review of Educational Research, 86(1), 42–78.",
    "Ma, W., Adesope, O. O., Nesbit, J. C., & Liu, Q. (2014). Intelligent tutoring systems and "
    "learning outcomes: A meta-analysis. J. Educational Psychology, 106(4), 901–918.",
    "Pardos, Z. A., & Heffernan, N. T. (2010). Modeling individualization in a Bayesian "
    "networks implementation of knowledge tracing. UMAP 2010, 255–266.",
    "Pavlik, P. I., Cen, H., & Koedinger, K. R. (2009). Performance factors analysis. AIED "
    "2009, 531–538.",
    "Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond. UMUAI, "
    "27(3–5), 313–350.",
    "Piech, C., et al. (2015). Deep knowledge tracing. NeurIPS 28, 505–513.",
    "Robinson, J. A. (1965). A machine-oriented logic based on the resolution principle. "
    "Journal of the ACM, 12(1), 23–41.",
    "Russell, S. J., & Norvig, P. (2020). Artificial intelligence: A modern approach (4th ed.). "
    "Pearson.",
    "Shute, V. J. (2008). Focus on formative feedback. Review of Educational Research, 78(1), "
    "153–189.",
    "Stamper, J., Eagle, M., Barnes, T., & Croy, M. (2013). Experimental evaluation of "
    "automatic hint generation for a logic tutor. IJAIED, 22(1–2), 3–17.",
    "VanLehn, K. (2006). The behavior of tutoring systems. IJAIED, 16(3), 227–265.",
    "VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring "
    "systems, and other tutoring systems. Educational Psychologist, 46(4), 197–221.",
]

colw = Inches(6.15)
col_x = [Inches(0.3), Inches(6.65)]
half = (len(REFERENCES) + 1) // 2
columns = [REFERENCES[:half], REFERENCES[half:]]
for ci, refs in enumerate(columns):
    box, tf = add_textbox(s, col_x[ci], Inches(1.15), colw, Inches(4.95))
    for i, ref in enumerate(refs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(5)
        r = p.add_run()
        set_run(r, ref, size=9.5)

box, tf = add_textbox(s, Inches(0.3), Inches(6.25), Inches(12.7), Inches(0.75))
p = tf.paragraphs[0]
r = p.add_run()
set_run(
    r,
    "24 distinct citations verified (25 rows -- one seed citation resolved to two genuinely "
    "different 2006 Aleven et al. papers); 25-30 required by the brief. Confirm you have read "
    "each one before submitting; find and verify 2-6 more.",
    size=12,
    italic=True,
    color=RGBColor(0x40, 0x40, 0x40),
)

add_footer(s, 9)


# ========================================== SLIDE 10 -- Contribution & AI Disclosure
s = new_slide()
set_background_white(s)
add_title_bar(s, "10. Contribution Statement and AI Disclosure")

ROLE_ROWS = [
    ("Literature review", "to be confirmed by students", "to be confirmed by students"),
    ("Methodology & design", "to be confirmed by students", "to be confirmed by students"),
    ("Implementation", "to be confirmed by students", "to be confirmed by students"),
    ("Experimentation", "to be confirmed by students", "to be confirmed by students"),
    ("Analysis", "to be confirmed by students", "to be confirmed by students"),
    ("Code/design review, testing", "to be confirmed by students", "to be confirmed by students"),
    ("Report preparation", "to be confirmed by students", "to be confirmed by students"),
]
table = make_table(
    s,
    Inches(0.3),
    Inches(1.2),
    Inches(12.7),
    Inches(3.0),
    len(ROLE_ROWS) + 1,
    3,
    col_widths=[Inches(3.3), Inches(4.7), Inches(4.7)],
    font_size=11,
)
for c, h in enumerate(["Role", "CVS Ujwal", "Keshav Raj"]):
    fill_cell(table, 0, c, h, size=12, bold=True)
for i, (role, u, k) in enumerate(ROLE_ROWS, start=1):
    fill_cell(table, i, 0, role, size=11, bold=True, color=ACCENT)
    fill_cell(table, i, 1, u, size=10.5, italic=True, color=RGBColor(0x70, 0x70, 0x70))
    fill_cell(table, i, 2, k, size=10.5, italic=True, color=RGBColor(0x70, 0x70, 0x70))

box, tf = add_textbox(s, Inches(0.3), Inches(4.35), Inches(12.6), Inches(0.35))
p = tf.paragraphs[0]
r = p.add_run()
set_run(r, "AI disclosure", size=14, bold=True, color=ACCENT)

AI_ROWS = [
    (
        "Claude Code (Opus 5 / Sonnet 5)",
        "Wrote core/app/api/cli/frontend, tests, tooling, HLD",
        "81/95 commits carry Co-Authored-By: Claude (Opus 5 or Sonnet 5)",
    ),
    ("claude.ai chat (web)", "Ideation, design review, prompt drafting", "[STUDENTS WRITE]"),
    (
        "AI-generated evaluation sets",
        'data/eval/*.json, 15 items each, labelled "AI-generated (Claude)"',
        "[STUDENTS WRITE]",
    ),
    ("Pilot forms", "docs/pilot/*.md drafted by Claude Code, sprint S8", "[STUDENTS WRITE]"),
]
table2 = make_table(
    s,
    Inches(0.3),
    Inches(4.75),
    Inches(12.7),
    Inches(2.2),
    len(AI_ROWS) + 1,
    3,
    col_widths=[Inches(3.3), Inches(5.5), Inches(3.9)],
    font_size=11,
)
for c, h in enumerate(["Tool", "Purpose / extent", "What humans did"]):
    fill_cell(table2, 0, c, h, size=12, bold=True)
for i, (tool, purpose, humans) in enumerate(AI_ROWS, start=1):
    is_blank = humans == "[STUDENTS WRITE]"
    fill_cell(table2, i, 0, tool, size=10.5, bold=True, color=ACCENT)
    fill_cell(table2, i, 1, purpose, size=10)
    fill_cell(
        table2,
        i,
        2,
        humans,
        size=10,
        italic=is_blank,
        color=RGBColor(0x70, 0x70, 0x70) if is_blank else None,
    )

add_footer(s, 10)


# =========================================== SLIDE 11 -- Appendix: Interface Screenshots
s = new_slide()
set_background_white(s)
add_title_bar(s, "Appendix: Interface, Live Run 2026-10-25")

SHOT_W = Inches(5.9)
SHOT_H = Inches(3.78)  # screenshots are 1400x900px, aspect ratio preserved
shots = [
    ("docs/screenshots/03_prove_screen.png", "Prove screen: symbol legend + plain-English clauses"),
    ("docs/screenshots/04_explanation_screen.png", "Explanation screen: completed proof trace"),
]
shot_x = [Inches(0.35), Inches(6.75)]
for (path, caption), x in zip(shots, shot_x, strict=True):
    s.shapes.add_picture(path, x, Inches(1.25), width=SHOT_W, height=SHOT_H)
    box, tf = add_textbox(s, x, Inches(5.1), SHOT_W, Inches(0.5))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, caption, size=12, italic=True, color=RGBColor(0x50, 0x50, 0x50))

add_footer(s, 11)


prs.save("docs/report/ProofPilot_Progress_Report.pptx")
print("Saved docs/report/ProofPilot_Progress_Report.pptx with", len(prs.slides), "slides")
