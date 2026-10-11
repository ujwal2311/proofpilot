"""Structural guards on the core package (docs/HLD.md v2.7 A2, v2.11).

These are boundaries that no amount of care enforces by itself, because breaking one of them
produces working code. A module name that shadows the standard library imports fine. A second
module that edits `State` reads fine. Both are found only by looking at the package as a whole.
"""

import ast
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "core"

# The ONE module allowed to write a session (v2.11). `models.py` defines the type -- a ClassDef,
# not a call -- so it is not an exception and does not need to be listed.
STATE_WRITER = "session.py"


def test_no_core_module_shadows_the_stdlib() -> None:
    # A core module named `types` would be imported in preference to the real standard-library
    # one by everything inside the package, and the failure would surface far from its cause.
    # Checked for every future module, not just the one that prompted the rule.
    clashes = sorted(
        path.stem
        for path in CORE.glob("*.py")
        if path.stem != "__init__" and path.stem in sys.stdlib_module_names
    )
    assert not clashes, f"core modules shadow stdlib names: {clashes}"


def _writes_state(source: str) -> list[str]:
    """Calls that construct or copy a `State`, by name. `ast`, never a grep.

    A grep cannot tell `State(` in code from `State` in a docstring, and this project has already
    had two tests fail on their own explanatory prose.

    The three forms that write a session, and nothing else:

      State(...)              /  models.State(...)      -- construction
      replace(...)            -- `from dataclasses import replace`, which is how session.py does it
      dataclasses.replace(...)

    The RECEIVER matters. A first draft matched any attribute call named `replace` and flagged
    `text.replace(short, long)` in english.py and `raw.split().replace(...)` in logic.py -- string
    methods, nothing to do with a session. It is still name-based rather than type-inferred, so a
    `replace()` imported from dataclasses and used on some other dataclass would be reported;
    that is the safe direction for a boundary guard to be wrong in.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        call = node.func
        if isinstance(call, ast.Name) and call.id in ("State", "replace"):
            found.append(f"{call.id}() at line {node.lineno}")
        elif isinstance(call, ast.Attribute) and (
            call.attr == "State"
            or (
                call.attr == "replace"
                and isinstance(call.value, ast.Name)
                and call.value.id == "dataclasses"
            )
        ):
            found.append(f"{call.attr}() at line {node.lineno}")
    return found


def test_only_session_writes_a_state() -> None:
    """`State` is written by exactly ONE core module (v2.11, the team's split condition).

    `tutor.py` is policy and `session.py` is mechanics, and the point of the split is that the
    module deciding what a student's action MEANS cannot also edit the session it happened in.
    While both lived together a change to either could reach the other, and nothing would have
    said so.

    Enforced structurally rather than by review: a second `dataclasses.replace(state, ...)`
    somewhere in core is working code that reads perfectly well, and it would quietly give the
    session two owners again.
    """
    offenders = {}
    for path in sorted(CORE.glob("*.py")):
        if path.name == STATE_WRITER:
            continue
        if writes := _writes_state(path.read_text(encoding="utf-8")):
            offenders[path.name] = writes
    assert not offenders, f"only {STATE_WRITER} may write a State; found {offenders}"


def test_session_really_is_the_writer_so_the_guard_is_not_vacuous() -> None:
    # A guard that would pass on an empty package is a guard nobody should trust. If the writes
    # ever move out of session.py, this fails and the test above stops meaning anything.
    source = (CORE / STATE_WRITER).read_text(encoding="utf-8")
    assert _writes_state(source), f"{STATE_WRITER} writes no State; has the split been undone?"
