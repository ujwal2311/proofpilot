"""Parser and evaluator for a student's typed propositional formula.

Accepted symbols are one capital letter, parentheses, and negation, conjunction,
disjunction, implication, and equivalence in ASCII or Unicode. Invalid input
raises ``FormulaError``; the caller must never fill in a missing connective.
"""

import re
from dataclasses import dataclass


class FormulaError(ValueError):
    """A formula the controlled typed grammar cannot interpret."""


@dataclass(frozen=True)
class Symbol:
    name: str


@dataclass(frozen=True)
class Not:
    item: "Formula"


@dataclass(frozen=True)
class Binary:
    left: "Formula"
    op: str
    right: "Formula"


Formula = Symbol | Not | Binary
_TOKEN = re.compile(r"\s*(<->|->|[~!¬&∧|∨→↔()]|[A-Z])")
_OPERATORS = {"!": "~", "¬": "~", "∧": "&", "∨": "|", "→": "->", "↔": "<->"}


def _tokens(text: str) -> tuple[str, ...]:
    """Split every supported token, refusing any unconsumed character."""
    found, index = [], 0
    while index < len(text):
        match = _TOKEN.match(text, index)
        if match is None:
            raise FormulaError(f"unsupported token at character {index + 1}")
        found.append(_OPERATORS.get(match.group(1), match.group(1)))
        index = match.end()
    if not found:
        raise FormulaError("formula is empty")
    return tuple(found)


class _Parser:
    """Recursive descent with the standard precedence: ~, &, |, ->, <->."""

    def __init__(self, tokens: tuple[str, ...]) -> None:
        self.tokens, self.index = tokens, 0

    def parse(self) -> Formula:
        formula = self._binary("<->", self._implies)
        if self.index != len(self.tokens):
            raise FormulaError(f"unexpected token {self.tokens[self.index]!r}")
        return formula

    def _implies(self) -> Formula:
        left = self._binary("|", self._and)
        if self._take("->"):
            return Binary(left, "->", self._implies())
        return left

    def _and(self) -> Formula:
        return self._binary("&", self._primary)

    def _binary(self, operator: str, operand) -> Formula:
        left = operand()
        while self._take(operator):
            left = Binary(left, operator, operand())
        return left

    def _primary(self) -> Formula:
        if self._take("~"):
            return Not(self._primary())
        if self._take("("):
            formula = self._binary("<->", self._implies)
            if not self._take(")"):
                raise FormulaError("missing closing parenthesis")
            return formula
        if self.index < len(self.tokens) and self.tokens[self.index].isalpha():
            name = self.tokens[self.index]
            self.index += 1
            return Symbol(name)
        raise FormulaError("expected a proposition symbol or parenthesized formula")

    def _take(self, token: str) -> bool:
        if self.index < len(self.tokens) and self.tokens[self.index] == token:
            self.index += 1
            return True
        return False


def parse(text: str) -> Formula:
    """Parse one complete typed formula."""
    return _Parser(_tokens(text)).parse()


def evaluate(formula: Formula, row: dict[str, bool]) -> bool:
    """Evaluate a formula on one assignment, refusing an unnamed proposition."""
    match formula:
        case Symbol(name):
            if name not in row:
                raise FormulaError(f"no value for symbol {name!r}")
            return row[name]
        case Not(item):
            return not evaluate(item, row)
        case Binary(left, "&", right):
            return evaluate(left, row) and evaluate(right, row)
        case Binary(left, "|", right):
            return evaluate(left, row) or evaluate(right, row)
        case Binary(left, "->", right):
            return not evaluate(left, row) or evaluate(right, row)
        case Binary(left, "<->", right):
            return evaluate(left, row) == evaluate(right, row)
    raise TypeError(f"unknown formula: {formula!r}")


def symbols(formula: Formula) -> tuple[str, ...]:
    """Return the formula's proposition symbols in canonical order."""
    match formula:
        case Symbol(name):
            return (name,)
        case Not(item):
            return symbols(item)
        case Binary(left, _, right):
            return tuple(sorted(set(symbols(left)) | set(symbols(right))))
    raise TypeError(f"unknown formula: {formula!r}")
