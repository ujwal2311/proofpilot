"""Formula AST to clause form, by the textbook three-step algorithm.

See docs/HLD.md section 6.2. Eliminate the implications, push negations inward with De Morgan,
then distribute disjunction over conjunction. The usual objection to general CNF conversion --
exponential blow-up from that last step -- does not apply here: the grammar is flat, so a formula
is at most three levels deep and the worst case is bounded at 25 clauses.

This module also owns negating the goal, because that is the same three steps on a different
input. It knows nothing about facts: the caller supplies `literal_of`, so symbols and polarity
stay core.facts' business.
"""

from collections.abc import Callable

from src.core.english import And, Atom, Iff, Implies, Node, Not, Or
from src.core.logic import Clause, canonical, is_tautology
from src.core.models import ConversionStep

LiteralOf = Callable[[str], str]


def eliminate(node: Node) -> Node:
    """Remove -> and <->, leaving only And, Or, Not and Atom."""
    match node:
        case Atom():
            return node
        case Not(item):
            return Not(eliminate(item))
        case And(items):
            return And(tuple(eliminate(i) for i in items))
        case Or(items):
            return Or(tuple(eliminate(i) for i in items))
        case Implies(antecedent, consequent):
            return Or((Not(eliminate(antecedent)), eliminate(consequent)))
        case Iff(left, right):
            a, b = eliminate(left), eliminate(right)
            return And((Or((Not(a), b)), Or((Not(b), a))))
    raise TypeError(f"not a formula node: {node!r}")


def push_negation(node: Node) -> Node:
    """Move every Not down onto an Atom, by De Morgan and double-negation cancellation.

    Runs after eliminate(), so a Not can only ever wrap an Atom, And, Or or another Not.
    """
    match node:
        case Not(Not(inner)):
            return push_negation(inner)
        case Not(And(items)):
            return Or(tuple(push_negation(Not(i)) for i in items))
        case Not(Or(items)):
            return And(tuple(push_negation(Not(i)) for i in items))
        case Not() | Atom():
            return node
        case And(items):
            return And(tuple(push_negation(i) for i in items))
        case Or(items):
            return Or(tuple(push_negation(i) for i in items))
    raise TypeError(f"not a negation-normal node: {node!r}")


def _parts(node: Node, kind: type) -> tuple[Node, ...]:
    """A node's operands if it is of `kind`, else the node itself as a single operand.

    Deliberately one level deep. `distribute` rebuilds bottom-up and flattens as it goes, so by
    the time anything calls this the operands are never themselves of the same kind -- a
    recursive version was written first and mutation testing showed it could not change any
    outcome (docs/experiments/mutation_log.md, C13).
    """
    return node.items if isinstance(node, kind) else (node,)


def distribute(node: Node) -> Node:
    """Push Or under And until the formula is a conjunction of disjunctions."""
    match node:
        case And(items):
            parts = tuple(part for i in items for part in _parts(distribute(i), And))
            return And(parts) if len(parts) > 1 else parts[0]
        case Or(items):
            done = tuple(distribute(i) for i in items)
            for index, item in enumerate(done):
                if isinstance(item, And):
                    rest = done[:index] + done[index + 1 :]
                    return distribute(And(tuple(Or((*rest, branch)) for branch in item.items)))
            parts = tuple(part for i in done for part in _parts(i, Or))
            return Or(parts) if len(parts) > 1 else parts[0]
    return node


def _literals(node: Node, literal_of: LiteralOf) -> Clause:
    """Collect one disjunction's literals."""
    return frozenset(
        literal_of(part.item.phrase).lstrip("~")
        if isinstance(part, Not) and literal_of(part.item.phrase).startswith("~")
        else f"~{literal_of(part.item.phrase)}"
        if isinstance(part, Not)
        else literal_of(part.phrase)
        for part in _parts(node, Or)
    )


def to_clauses(node: Node, literal_of: LiteralOf) -> list[Clause]:
    """Run the three steps and return canonical, tautology-free, duplicate-free clauses.

    A tautological clause is always true, so dropping it cannot change what the set means --
    but keeping it would give the search a clause it can never use.
    """
    normal = distribute(push_negation(eliminate(node)))
    seen: set[Clause] = set()
    for disjunction in _parts(normal, And):
        clause = _literals(disjunction, literal_of)
        if not is_tautology(clause):
            seen.add(clause)
    return sorted(seen, key=canonical)


def premise_clauses(node: Node, literal_of: LiteralOf) -> list[Clause]:
    """Clause form of a premise, exactly as written."""
    return to_clauses(node, literal_of)


def goal_clauses(node: Node, literal_of: LiteralOf) -> list[Clause]:
    """Clause form of the NEGATED conclusion, which is what a refutation needs.

    Lives here rather than in entail.py because it is the same three steps on a different input;
    entail.py owns truth tables, not formula rewriting.
    """
    return to_clauses(Not(node), literal_of)


def _text(node: Node, literal_of: LiteralOf) -> str:
    """One formula as text, in the same connective spelling `core/formula.py` parses (M2) --
    one notation for a typed formula across the system, not a second one invented here."""
    match node:
        case Atom(phrase):
            return literal_of(phrase)
        case Not(Atom(phrase)):
            lit = literal_of(phrase)
            return lit[1:] if lit.startswith("~") else f"~{lit}"
        case Not(item):
            # Only reachable mid-algorithm: the parsed grammar never nests Not this deep, but
            # `eliminate`'s own output legitimately does, one step before `push_negation` clears
            # it -- this function renders what IS there, not what the grammar promises.
            return f"~{_text(item, literal_of)}"
        case And(items):
            return "(" + " & ".join(_text(i, literal_of) for i in items) + ")"
        case Or(items):
            return "(" + " | ".join(_text(i, literal_of) for i in items) + ")"
        case Implies(antecedent, consequent):
            return f"({_text(antecedent, literal_of)} -> {_text(consequent, literal_of)})"
        case Iff(left, right):
            return f"({_text(left, literal_of)} <-> {_text(right, literal_of)})"
    raise TypeError(f"not a formula node: {node!r}")


# Paired with the three real functions above, in the order `to_clauses` runs them. A law that
# does not change the formula is not recorded -- the Explanation screen shows what happened, not
# every law that was merely checked.
_LAWS = (("Elimination", eliminate), ("De Morgan", push_negation), ("Distribution", distribute))


def conversion_steps(node: Node, literal_of: LiteralOf) -> tuple[ConversionStep, ...]:
    """The textbook 3-step algorithm, narrated -- the same transform `to_clauses` runs, traced.

    Does not alter `eliminate`/`push_negation`/`distribute` or change what they compute; this
    only renders each one's input and output as text and keeps the steps where they differ.
    """
    steps = []
    current = node
    for law, transform in _LAWS:
        before = _text(current, literal_of)
        current = transform(current)
        after = _text(current, literal_of)
        if before != after:
            steps.append(ConversionStep(law, before, after))
    return tuple(steps)
