"""The adapters are I/O only: no decisions, no wording (sprint item 1).

    core/        decides everything
    app/         the shared edge: loads and validates, prepares text, renders codes, owns ids
    cli.py       read a line, call app, print
    api/*.py     parse a body, call app, return JSON

The rule worth enforcing mechanically is the WORDING one, because it is the one that erodes by
convenience rather than by decision. Nobody sets out to put a second copy of the feedback text in
the API; someone adds one helpful f-string during debugging, then another, and six months later
the CLI and the browser tell a student two different things about the same mistake and nothing
ever said so.

So: any string constant in an adapter that reads like a sentence to a student fails the build. The
threshold is four or more words, which is low enough to catch "that step is not valid here" and
high enough to leave `"--script"`, `"VALID"` and `f"{name}: {body}"` alone.

Docstrings and comments are exempt -- they are for the reader of the code, not the student -- and
`data/messages.yaml` is where the sentences go.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
WORD_LIMIT = 4


def _is_only_a_docstring(path: Path) -> bool:
    """A package marker, not an adapter. Judged by the parsed BODY, not by file size.

    `api/__init__.py` holds a one-line docstring and nothing else, so a size check called it an
    adapter and then failed it for not importing anything.
    """
    body = ast.parse(path.read_text(encoding="utf-8")).body
    return len(body) <= 1 and all(
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) for node in body
    )


# Globbed, so an API module added later is covered without anyone remembering to add it.
ADAPTERS = [
    path
    for path in [SRC / "cli.py", *sorted((SRC / "api").glob("*.py"))]
    if not _is_only_a_docstring(path)
]


def docstring_ids(tree: ast.AST) -> set[int]:
    """The exact string nodes that are docstrings.

    Found by walking the nodes that can HAVE one, rather than guessing from position: a module
    whose first statement is an assignment has no docstring, and a bare string used as a
    pseudo-comment is not one either.

    Shared by both checks below, because both have to ignore prose. The data-file check without
    it reported `cli.py` for the phrase "`data/messages.yaml`" in its own module docstring --
    which is the module EXPLAINING that it does not load the file.
    """
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def sentences_in(source: str) -> list[tuple[int, str]]:
    """String constants of >= WORD_LIMIT words that are not docstrings.

    Docstrings are found by walking the nodes that can HAVE one and remembering the exact string
    object, rather than by guessing from position: a module whose first statement is an assignment
    has no docstring, and a bare string used as a pseudo-comment is not one either.
    """
    tree = ast.parse(source)
    docstrings = docstring_ids(tree)

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            # Count real words: a format placeholder is not a word a student reads, and neither
            # is a run of punctuation used as a separator.
            words = [
                w for w in node.value.replace("{", " ").replace("}", " ").split() if w.isalpha()
            ]
            if len(words) >= WORD_LIMIT:
                found.append((node.lineno, node.value))
    return found


@pytest.mark.parametrize("path", ADAPTERS, ids=lambda p: p.name)
def test_adapters_hold_no_user_facing_wording(path: Path) -> None:
    offenders = sentences_in(path.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{path.name} contains sentences a student could read: {offenders}. "
        f"Wording belongs in data/messages.yaml, rendered by app/render.py -- otherwise the CLI "
        f"and the API drift apart about what the same outcome is called."
    )


def test_the_check_would_actually_catch_a_sentence() -> None:
    # A guard nobody has seen fail is a guard nobody should trust. The first case is the realistic
    # mistake; the rest are the things that must NOT trip it or the check gets switched off.
    caught = sentences_in('x = "that step is not valid here"\n')
    assert len(caught) == 1

    for innocent in (
        '"""A module docstring with plenty of words in it."""\nx = 1\n',
        'f = "--script"\nc = "VALID"\nk = "CLAIM_ACCEPTED"\n',
        'x = f"{name}: {body}"\n',
        'd = {"a": 1}\nimport os\n',
        'def f():\n    """Several words of explanation for the reader."""\n    return 1\n',
        'class C:\n    """Several words of explanation for the reader."""\n',
    ):
        assert sentences_in(innocent) == [], innocent


def test_every_adapter_is_actually_checked() -> None:
    # The list is built by glob, so an API module added later is covered automatically -- but an
    # empty list would make the parametrized test vacuous and pass silently.
    assert ADAPTERS, "no adapters found to check"
    assert (SRC / "cli.py") in ADAPTERS


# A module that DRIVES the system -- a command loop or an HTTP route table. `api/schemas.py` is
# not one: it is the API's data contract, it makes no decisions, and requiring it to import the
# shared edge would be requiring an import it has no use for.
DRIVERS = [path for path in ADAPTERS if path.name in ("cli.py", "main.py")]


def test_no_adapter_reads_a_data_file_itself() -> None:
    """`app/data.py` is the only loader. An adapter with its own `yaml.safe_load` would mean two
    copies of the validation, and the one a student hit would depend on which client they used.
    """
    for path in ADAPTERS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        # Loading a data file requires NAMING one, so that is what the check looks for: the
        # `yaml` module, or a string that points into `data/`.
        #
        # The first version matched any `open()` or `.load()` call and flagged two innocents in
        # `cli.py`: `open()` on the `--script` path, which is a replay file for tests, and
        # `Runtime.load()`, which is the shared loader being called correctly -- the very thing
        # the rule wants. A guard that fires on correct use gets switched off.
        assert "yaml" not in modules, f"{path.name} imports yaml; app/data.py is the only loader"
        prose = docstring_ids(tree)
        named = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in prose
            and ("data/" in node.value or node.value.endswith((".yaml", ".json")))
        ]
        assert not named, f"{path.name} names a data file {named}; app/data.py is the loader"


def test_the_drivers_import_the_shared_edge_rather_than_reimplementing_it() -> None:
    """A driver must go through `app`, not around it.

    One that loaded `messages.yaml` itself, or built its own clause ids, would pass the wording
    check above while still duplicating the thing `app/` exists to hold once.
    """
    assert DRIVERS, "no driver modules found; the check would be vacuous"
    for path in DRIVERS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert any(m == "src" or m.startswith("src.app") for m in modules), (
            f"{path.name} does not import the shared edge"
        )
