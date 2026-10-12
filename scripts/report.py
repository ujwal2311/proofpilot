"""Shared glue for the evaluation scripts: the commit stamp and a markdown table writer.

Every output file in docs/experiments and docs/pilot is stamped with date, git commit hash,
Python version and OS (CLAUDE.md rule 10 — a number without its provenance cannot be checked
later). Four scripts needing this is how three of them drift if each writes its own copy.
"""

import platform
import subprocess
import sys
from datetime import date


def commit_hash() -> str:
    """The short hash of HEAD, or 'uncommitted' if there is none yet (a fresh checkout)."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, check=True
        )
        return done.stdout.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return "uncommitted"


def stamp_line() -> str:
    """One markdown line: date, commit, Python version, OS — the provenance every number needs."""
    return (
        f"**Date:** {date.today()}. **Commit:** `{commit_hash()}`. "
        f"**Python:** {sys.version.split()[0]}. **OS:** {platform.platform()}."
    )


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """A GitHub-flavoured markdown table from headers and string rows."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)
