"""Structural guards on the core package (docs/HLD.md v2.7 A2)."""

import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "core"


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
