"""Phase 1 smoke test: the scaffold is wired correctly and core is web-framework-free.

This is deliberately not a tautology. It fails if pytest.ini's pythonpath is wrong, if the
interpreter is older than the project floor, or if anything under src/core ever starts pulling in
a web framework -- the architectural invariant from docs/HLD.md section 4. The subprocess check
grows into `test_core_has_no_web_imports` in Phase 2 as real modules land.
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)
FORBIDDEN_IN_CORE = ("fastapi", "pydantic", "starlette", "uvicorn")


def test_scaffold_imports_and_core_is_web_free() -> None:
    assert sys.version_info >= MIN_PYTHON, f"Python {MIN_PYTHON}+ required, got {sys.version_info}"

    import src.core  # proves pytest.ini's `pythonpath = backend` resolves

    assert src.core.__doc__, "core package should document its no-web-imports contract"

    # Run in a clean interpreter: pytest's own imports would otherwise mask a real violation.
    probe = (
        "import sys; import src.core; "
        f"hits=[m for m in {FORBIDDEN_IN_CORE!r} if m in sys.modules]; "
        "print(','.join(hits))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", f"core pulled in web packages: {result.stdout.strip()}"
