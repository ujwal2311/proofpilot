"""Docs must reference the HLD version that docs/HLD.md actually declares.

Version drift is silent and embarrassing: a reading guide pointing at a superseded design reads
as carelessness in a viva. The HLD itself is excluded -- its change log cites old versions on
purpose.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERRING_DOCS = ("CLAUDE.md", "README.md", "docs/READING_GUIDE.md")
VERSION_TOKEN = re.compile(r"v(\d+\.\d+)")


def test_docs_reference_current_hld_version() -> None:
    header = (ROOT / "docs" / "HLD.md").read_text(encoding="utf-8").splitlines()[0]
    current = re.search(r"v(\d+\.\d+)", header).group(1)

    for name in REFERRING_DOCS:
        path = ROOT / name
        stale = set(VERSION_TOKEN.findall(path.read_text(encoding="utf-8"))) - {current}
        assert not stale, f"{name} references v{sorted(stale)}; docs/HLD.md declares v{current}"
