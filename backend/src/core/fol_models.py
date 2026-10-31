"""First-order-logic data model: terms, predicates, formulas, clauses, substitutions.

See docs/HLD.md section 18.1. This module owns SHAPE ONLY -- no parsing (core.fol_english), no
CNF conversion (core.fol_cnf), no unification (core.unify). It reads no files and validates
nothing beyond what Python's type system gives for free, exactly like core.models and the Node
types in core.english: invariants are enforced by the code that CONSTRUCTS these values (the
grammar, the CNF pipeline, the Skolemizer), not by the dataclasses themselves.

CONTRACT.

  Term = Variable | Constant | FunctionTerm      -- see each class for its invariant.
  Predicate(name, args)                          -- args may be empty (the propositional bridge).
  FolLiteral = tuple[bool, Predicate]             -- True = positive, False = negative.
  FolFormula = Predicate | FolNot | FolAnd | FolOr | FolImplies | FolIff | ForAll | Exists
  FolClause = frozenset[FolLiteral]               -- a disjunction; remaining vars are implicit-∀.
  Substitution = dict[str, Term]                  -- variable name -> Term, never mutated in place.

Everything here is a frozen dataclass holding only tuples (never lists), for the same reason as
core.models: a clause must be hashable for the BFS visited set, and immutability must be
structural rather than promised, because this project replays state rather than mutating it in
place. `Fol`-prefixed connective names (FolNot/FolAnd/.../FolIff) avoid colliding with
core.english's Not/And/Or/Implies/Iff if the two modules are ever imported side by side.

EDGE CASE: quantifier order is never normalised or reordered anywhere in this file.
`ForAll(x, Exists(y, P(x, y)))` and `Exists(y, ForAll(x, P(x, y)))` are different trees and must
stay different objects -- collapsing them would be exactly the kind of silent guess CLAUDE.md
principle 2 forbids.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Variable:
    """A quantified or implicitly-universal name, e.g. "x", "y1". Lowercase by convention --
    enforced by whatever constructs one (the grammar, standardize_variables, skolemize), not here.
    """

    name: str


@dataclass(frozen=True)
class Constant:
    """A specific individual, e.g. "socrates", "sk_c0" (a Skolem constant). Normalised to
    lowercase by the grammar that builds one; this class accepts whatever string it is given.
    """

    name: str


@dataclass(frozen=True)
class FunctionTerm:
    """A function term, e.g. a Skolem function `sk_f0(x)`. `args` is non-empty by construction --
    a nullary function is a `Constant` instead, so there is exactly one representation of "no
    arguments" rather than two that could silently disagree.
    """

    name: str
    args: tuple["Term", ...]


Term = Variable | Constant | FunctionTerm


@dataclass(frozen=True)
class Predicate:
    """An atomic formula, e.g. `Human(x)`, or `Loves(alice, bob)`. `args == ()` is a
    zero-argument predicate -- the bridge that makes a FOL predicate double as a propositional
    atom (section 18.1), used nowhere in propositional mode but available so the two type unions
    can share this one class instead of each defining their own.
    """

    name: str
    args: tuple[Term, ...]


FolLiteral = tuple[bool, Predicate]


@dataclass(frozen=True)
class FolNot:
    body: "FolFormula"


@dataclass(frozen=True)
class FolAnd:
    items: tuple["FolFormula", ...]


@dataclass(frozen=True)
class FolOr:
    items: tuple["FolFormula", ...]


@dataclass(frozen=True)
class FolImplies:
    antecedent: "FolFormula"
    consequent: "FolFormula"


@dataclass(frozen=True)
class FolIff:
    left: "FolFormula"
    right: "FolFormula"


@dataclass(frozen=True)
class ForAll:
    """Universal quantification. `var` binds `body`; nesting a second quantifier on the same
    variable name is legal to construct (standardize_variables exists precisely to remove the
    ambiguity that would otherwise cause, not to make it unconstructable).
    """

    var: Variable
    body: "FolFormula"


@dataclass(frozen=True)
class Exists:
    """Existential quantification. See `ForAll` -- same shape, opposite quantifier."""

    var: Variable
    body: "FolFormula"


FolFormula = Predicate | FolNot | FolAnd | FolOr | FolImplies | FolIff | ForAll | Exists

FolClause = frozenset[FolLiteral]
Substitution = dict[str, Term]
