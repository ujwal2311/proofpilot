"""Truth-table checking and fixed diagnoses for typed formula translations."""

from dataclasses import dataclass

from src.core.formula import Binary, Formula, Not, evaluate, parse, symbols


@dataclass(frozen=True)
class TranslationResult:
    """A translation diagnosis and, when needed, one readable counterexample row."""

    code: str
    counterexample: tuple[tuple[str, bool], ...] | None = None


def _rows(formulas: tuple[Formula, ...]):
    names = tuple(sorted({name for formula in formulas for name in symbols(formula)}))
    for number in range(1 << len(names)):
        yield {name: bool(number >> index & 1) for index, name in enumerate(names)}


def _equivalent(left: Formula, right: Formula) -> tuple[bool, dict[str, bool] | None]:
    for row in _rows((left, right)):
        if evaluate(left, row) != evaluate(right, row):
            return False, row
    return True, None


def _contrapositive(formula: Formula) -> Formula | None:
    if isinstance(formula, Binary) and formula.op == "->":
        return Binary(Not(formula.right), "->", Not(formula.left))
    return None


def _drop_negation(formula: Formula) -> Formula | None:
    if isinstance(formula, Not):
        return formula.item
    if isinstance(formula, Binary):
        left = _drop_negation(formula.left)
        if left is not None:
            return Binary(left, formula.op, formula.right)
        right = _drop_negation(formula.right)
        if right is not None:
            return Binary(formula.left, formula.op, right)
    return None


def _mutations(reference: Formula) -> tuple[tuple[str, Formula], ...]:
    candidates: list[tuple[str, Formula]] = []
    if isinstance(reference, Binary) and reference.op == "->":
        candidates.append(("CONVERSE", Binary(reference.right, "->", reference.left)))
    if missing := _drop_negation(reference):
        candidates.append(("MISSING_NEGATION", missing))
    if isinstance(reference, Binary) and reference.op in {"&", "|"}:
        operator = "|" if reference.op == "&" else "&"
        candidates.append(("AND_OR_SWAP", Binary(reference.left, operator, reference.right)))
    return tuple(candidates)


def _english_row(row: dict[str, bool], labels: dict[str, str]) -> tuple[tuple[str, bool], ...]:
    return tuple((labels.get(symbol, symbol), value) for symbol, value in sorted(row.items()))


def check(reference_text: str, student_text: str, labels: dict[str, str]) -> TranslationResult:
    """Compare a student formula to the reference by exhaustive truth table.

    Contraposition is recognised only when the student wrote that exact shape;
    all other equivalent spellings are correct. The three fixed mistakes are
    tested in the documented order, then every remaining difference is named
    ``NOT_EQUIVALENT`` with the first canonical counterexample.
    """
    reference, student = parse(reference_text), parse(student_text)
    contraposition = _contrapositive(reference)
    if contraposition is not None and student == contraposition:
        return TranslationResult("CORRECT_CONTRAPOSITIVE")
    equivalent, witness = _equivalent(reference, student)
    if equivalent:
        return TranslationResult("CORRECT")
    for code, mutation in _mutations(reference):
        if _equivalent(student, mutation)[0]:
            return TranslationResult(code, _english_row(witness or {}, labels))
    return TranslationResult("NOT_EQUIVALENT", _english_row(witness or {}, labels))
