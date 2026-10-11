"""Phase 1 smoke test: the scaffold is wired correctly and core imports nothing third-party.

The import guard is an ALLOWLIST, not a denylist. A denylist only catches the packages someone
thought to name; this asserts that importing src.core adds nothing beyond the standard library
and the project's own package, so a future `import httpx`, `import yaml` or `import numpy` in
core fails without anyone having to predict it. See docs/HLD.md section 4 -- core is pure Python
and takes its configuration as plain data from the edge (cli/api/scripts).

The probe runs in a clean subprocess: pytest and its plugins have already imported a great deal
in-process, which would mask a real violation.
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 12)  # single source of truth: pyproject.toml `requires-python`
OWN_PACKAGE = "src"

# EVERY submodule, not just the package. `core/__init__.py` imports none of them, so importing
# the package alone proved almost nothing: a `import pydantic` inside `session.py` would have
# sailed through. Found while introducing pydantic at the EDGE (S3) -- the guard that was supposed
# to stop it reaching core could not have seen it.
_PROBE = f"""
import pkgutil, sys
import {OWN_PACKAGE}.core as core
baseline = set(sys.modules)
for found in pkgutil.iter_modules(core.__path__):
    __import__(f"{OWN_PACKAGE}.core.{{found.name}}")
added = {{m.split(".")[0] for m in set(sys.modules) - baseline}}
foreign = sorted(m for m in added if m not in sys.stdlib_module_names and m != {OWN_PACKAGE!r})
print(",".join(foreign))
"""


def test_scaffold_imports_and_core_uses_only_stdlib() -> None:
    assert sys.version_info >= MIN_PYTHON, f"Python {MIN_PYTHON}+ required, got {sys.version_info}"

    import src.core  # proves pytest.ini's `pythonpath = backend` resolves

    assert src.core.__doc__, "core package should document its no-third-party-imports contract"

    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
    )
    foreign = result.stdout.strip()
    assert foreign == "", f"core imported non-stdlib package(s): {foreign}"
