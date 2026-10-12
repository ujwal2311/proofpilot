"""Bans the builtin `hash()` from backend/src and scripts (sprint note 2026-10-12).

`hash()` is randomised per PROCESS by default for str/bytes (`PYTHONHASHSEED`), so anything
seeded, keyed or ordered by it looks deterministic on one run and is not across two -- exactly
what broke `scripts/run_experiments.py`'s hint-soundness walk the first time it was run twice and
diffed. Rule 4 says seed every generator from `core/config.py`; `hash()` cannot be, because
nothing in this process controls what it returns from one run to the next.

`__hash__` method definitions are untouched -- a dataclass needing to be hashable is normal and
unrelated to this rule. Only a CALL to the builtin `hash(...)` is banned.

An entry may be added to ALLOWLIST with a one-line reason if a call is truly needed and provably
has no effect on output or determinism (e.g. purely a cache-size heuristic, never seeding or
ordering anything) -- empty today, because the one real use found by the sweep was fixed instead
of excused.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = (ROOT / "backend" / "src", ROOT / "scripts")

ALLOWLIST: dict[str, str] = {}


def _hash_calls(source: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash"
    ]


def test_no_builtin_hash_in_src_or_scripts() -> None:
    offenders = {}
    for target in TARGETS:
        for path in sorted(target.rglob("*.py")):
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            if rel in ALLOWLIST:
                continue
            if lines := _hash_calls(path.read_text(encoding="utf-8")):
                offenders[rel] = lines
    assert not offenders, (
        "builtin hash() is per-process randomised and must never drive seeding, ordering or "
        f"output: {offenders}. Add to this test's ALLOWLIST with a reason if truly needed."
    )
