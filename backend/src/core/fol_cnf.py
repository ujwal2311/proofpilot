"""First-order formula to clause form, by the standard 8-step algorithm.

See docs/HLD.md section 18.3. Each step is a pure function, tested independently, because FOL CNF
conversion (unlike the propositional 3-step version in core.cnf) has two steps -- quantifier De
Morgan and Skolemization -- where a wrong implementation produces a formula that still LOOKS
plausible but is unsound or incomplete. `to_fol_clauses` (added once all 8 steps exist) just
chains them in order; it owns no logic of its own.

This phase (FOL sprint Phase 2, HLD section 18.12) implements steps 1-3 only:
eliminate_iff_implies, push_negation_inward, standardize_variables. Steps 4-8 (skolemize,
drop_universal_quantifiers, distribute_and_over_or, flatten_to_clauses, standardize_apart_clauses)
and the `to_fol_clauses` pipeline function are added in Phase 3.
"""

from src.core.config import MAX_FOL_CLAUSES
from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolClause,
    FolFormula,
    FolIff,
    FolImplies,
    FolLiteral,
    FolNot,
    FolOr,
    ForAll,
    FunctionTerm,
    Predicate,
    Term,
    Variable,
)


def eliminate_iff_implies(f: FolFormula) -> FolFormula:
    """Rewrite FolIff and FolImplies away, recursively, including inside quantifier bodies.

    Mirrors core.cnf.eliminate() exactly, extended with ForAll/Exists recursion: quantifiers
    commute with this step (it only rewrites the connectives inside, never touches binders), so
    there is no FOL-specific subtlety here -- that subtlety is entirely in step 2.

    FolIff(A,B)     -> FolAnd(FolOr((FolNot(A'),B')), FolOr((FolNot(B'),A')))   -- built directly
                       from Or, not from FolImplies, so the result needs no second elimination
                       pass (same reason core.cnf.eliminate avoids it for Iff).
    FolImplies(A,B) -> FolOr((FolNot(A'), B'))
    """
    match f:
        case Predicate():
            return f
        case FolNot(body):
            return FolNot(eliminate_iff_implies(body))
        case FolAnd(items):
            return FolAnd(tuple(eliminate_iff_implies(i) for i in items))
        case FolOr(items):
            return FolOr(tuple(eliminate_iff_implies(i) for i in items))
        case FolImplies(antecedent, consequent):
            done_ante, done_cons = (
                eliminate_iff_implies(antecedent),
                eliminate_iff_implies(consequent),
            )
            return FolOr((FolNot(done_ante), done_cons))
        case FolIff(left, right):
            a, b = eliminate_iff_implies(left), eliminate_iff_implies(right)
            return FolAnd((FolOr((FolNot(a), b)), FolOr((FolNot(b), a))))
        case ForAll(var, body):
            return ForAll(var, eliminate_iff_implies(body))
        case Exists(var, body):
            return Exists(var, eliminate_iff_implies(body))
    raise TypeError(f"not a FOL formula node: {f!r}")


def _push_not(body: FolFormula) -> FolFormula:
    """Push ONE FolNot past whatever it directly wraps -- extracted so push_negation_inward
    stays under the complexity gate; split here rather than simplified away, because each of
    these six cases is a distinct De Morgan law and merging any two would hide one.

    THE QUANTIFIER CASES (HLD section 18.3, step 2 warning -- most commonly missed rule):
    Not(ForAll(x, P)) is Exists(x, Not(P)), NOT ForAll(x, Not(P)) -- the quantifier flips, exactly
    as propositional De Morgan flips And/Or. Verified against the textbook rule (Russell & Norvig,
    CNF conversion step 2) and against HLD section 18.3's own pinned example:
    push_negation_inward(FolNot(ForAll(x, P(x)))) == Exists(x, FolNot(P(x))).
    """
    match body:
        case FolNot(inner):
            return push_negation_inward(inner)
        case FolAnd(items):
            return FolOr(tuple(push_negation_inward(FolNot(i)) for i in items))
        case FolOr(items):
            return FolAnd(tuple(push_negation_inward(FolNot(i)) for i in items))
        case ForAll(var, inner):
            return Exists(var, push_negation_inward(FolNot(inner)))
        case Exists(var, inner):
            return ForAll(var, push_negation_inward(FolNot(inner)))
        case Predicate():
            return FolNot(body)
    raise TypeError(
        f"not a negation-normal FOL node (did eliminate_iff_implies run first?): {body!r}"
    )


def push_negation_inward(f: FolFormula) -> FolFormula:
    """Move every FolNot down onto a Predicate, by De Morgan (propositional AND quantifier).

    Runs after eliminate_iff_implies(), so a FolNot can only wrap a Predicate, FolAnd, FolOr,
    ForAll, Exists, or another FolNot -- see `_push_not` for that case.
    """
    match f:
        case FolNot(body):
            return _push_not(body)
        case Predicate():
            return f
        case FolAnd(items):
            return FolAnd(tuple(push_negation_inward(i) for i in items))
        case FolOr(items):
            return FolOr(tuple(push_negation_inward(i) for i in items))
        case ForAll(var, body):
            return ForAll(var, push_negation_inward(body))
        case Exists(var, body):
            return Exists(var, push_negation_inward(body))
    raise TypeError(f"not a negation-normal FOL node (did eliminate_iff_implies run first?): {f!r}")


def _rename_term(term: Term, rename: dict[str, str]) -> Term:
    """Apply a variable rename map to one term. A name absent from `rename` is a free
    variable (or a different, not-yet-renamed scope) and is left exactly as it is."""
    match term:
        case Variable(name):
            return Variable(rename.get(name, name))
        case Constant():
            return term
        case FunctionTerm(name, args):
            return FunctionTerm(name, tuple(_rename_term(a, rename) for a in args))
    raise TypeError(f"not a term: {term!r}")


def _standardize(f: FolFormula, rename: dict[str, str], counter: list[int]) -> FolFormula:
    """`standardize_variables`'s recursion, carrying the ACTIVE rename map for the current
    lexical scope. A quantifier that rebinds an already-renamed name overwrites that one entry
    in its OWN copy of the map (`rename | {...}`) rather than mutating the caller's -- which is
    exactly what makes the most-closely-nested binder win, the way ordinary scoping does, instead
    of the outer rename leaking into a shadowed inner variable of the same original name.
    """
    match f:
        case Predicate(name, args):
            return Predicate(name, tuple(_rename_term(a, rename) for a in args))
        case FolNot(body):
            return FolNot(_standardize(body, rename, counter))
        case FolAnd(items):
            return FolAnd(tuple(_standardize(i, rename, counter) for i in items))
        case FolOr(items):
            return FolOr(tuple(_standardize(i, rename, counter) for i in items))
        case FolImplies(antecedent, consequent):
            return FolImplies(
                _standardize(antecedent, rename, counter), _standardize(consequent, rename, counter)
            )
        case FolIff(left, right):
            return FolIff(_standardize(left, rename, counter), _standardize(right, rename, counter))
        case ForAll(var, body) | Exists(var, body):
            fresh = Variable(f"v{counter[0]}")
            counter[0] += 1
            renamed_body = _standardize(body, rename | {var.name: fresh.name}, counter)
            quantifier = ForAll if isinstance(f, ForAll) else Exists
            return quantifier(fresh, renamed_body)
    raise TypeError(f"not a FOL formula node: {f!r}")


def standardize_variables(f: FolFormula, _counter: list[int] | None = None) -> FolFormula:
    """Alpha-rename every BOUND variable to a globally fresh name (v0, v1, ...).

    MUST run before Skolemization (step 4): skolemize() uses a formula's lexical nesting of
    ForAll to decide which universals a Skolem function depends on, and that reasoning silently
    breaks if two different quantifiers still share a variable name (variable capture -- see the
    HLD section 18.3 example). Free variables -- a Variable not bound by any ForAll/Exists in `f`
    -- are untouched, because they do not belong to this formula's own quantifier structure.

    `_counter` is an injectable one-element box (`[next_index]`) rather than module-level state,
    so that a fresh top-level call gets fresh names deterministically without relying on hidden
    global state between tests or between calls -- a cheaper way to get the same determinism
    HLD section 18.3 asks for than a module global would be, and one call to `to_fol_clauses()`
    (Phase 3) will supply one counter for the whole formula.
    """
    counter = _counter if _counter is not None else [0]
    return _standardize(f, {}, counter)


def _apply_term(term: Term, subst: dict[str, Term]) -> Term:
    """Apply a variable SUBSTITUTION (name -> an arbitrary Term, not just another name) to one
    term. Shares `Variable`/`Constant`/`FunctionTerm` structure with `_rename_term`, but that one
    only ever maps a name to another name; this one is what skolemize() needs to drop in a whole
    Skolem constant or function term."""
    match term:
        case Variable(name):
            return subst.get(name, term)
        case Constant():
            return term
        case FunctionTerm(name, args):
            return FunctionTerm(name, tuple(_apply_term(a, subst) for a in args))
    raise TypeError(f"not a term: {term!r}")


def _substitute(f: FolFormula, subst: dict[str, Term]) -> FolFormula:
    """Apply a term substitution throughout a formula. Assumes `f` has already been through
    standardize_variables (true for every caller in this pipeline), so no quantifier below `f`
    can rebind a name `subst` maps -- there is no shadowing left to protect against here."""
    match f:
        case Predicate(name, args):
            return Predicate(name, tuple(_apply_term(a, subst) for a in args))
        case FolNot(body):
            return FolNot(_substitute(body, subst))
        case FolAnd(items):
            return FolAnd(tuple(_substitute(i, subst) for i in items))
        case FolOr(items):
            return FolOr(tuple(_substitute(i, subst) for i in items))
        case FolImplies(antecedent, consequent):
            return FolImplies(_substitute(antecedent, subst), _substitute(consequent, subst))
        case FolIff(left, right):
            return FolIff(_substitute(left, subst), _substitute(right, subst))
        case ForAll(var, body) | Exists(var, body):
            quantifier = ForAll if isinstance(f, ForAll) else Exists
            return quantifier(var, _substitute(body, subst))
    raise TypeError(f"not a FOL formula node: {f!r}")


def _skolemize(f: FolFormula, universals: tuple[Variable, ...], counter: list[int]) -> FolFormula:
    match f:
        case Predicate():
            return f
        case FolNot(body):
            return FolNot(_skolemize(body, universals, counter))
        case FolAnd(items):
            return FolAnd(tuple(_skolemize(i, universals, counter) for i in items))
        case FolOr(items):
            return FolOr(tuple(_skolemize(i, universals, counter) for i in items))
        case ForAll(var, body):
            return ForAll(var, _skolemize(body, universals + (var,), counter))
        case Exists(var, body):
            term: Term = (
                FunctionTerm(f"sk_f{counter[0]}", universals)
                if universals
                else Constant(f"sk_c{counter[0]}")
            )
            counter[0] += 1
            body_without_y = _substitute(body, {var.name: term})
            return _skolemize(body_without_y, universals, counter)
    raise TypeError(
        f"not a FOL formula node (expected no Implies/Iff -- run eliminate_iff_implies "
        f"first): {f!r}"
    )


def skolemize(
    f: FolFormula, universals: tuple[Variable, ...] = (), _counter: list[int] | None = None
) -> FolFormula:
    """Replace each Exists with a fresh Skolem term, dropping the Exists wrapper.

    No enclosing ForAll (`universals` empty): Exists(y, P(y)) -> P[y -> a fresh Skolem CONSTANT]
    -- the existential witness does not depend on anything, so one fixed individual suffices.

    One or more enclosing ForAll: Exists(y, P(x1,...,xn,y)) -> P[y -> a fresh Skolem FUNCTION of
    x1,...,xn] -- the witness may depend on which x1,...,xn it was asked for, which is exactly
    what making it a function of them captures. `universals` is accumulated by recursing through
    ForAll, in the order the quantifiers were nested, before this function is reached.

    MUST run after standardize_variables (step 3): relies on there being no shadowing left to
    substitute through (see `_substitute`). `_counter` is injectable for the same determinism
    reason as `standardize_variables`'s -- see that function's docstring.
    """
    counter = _counter if _counter is not None else [0]
    return _skolemize(f, universals, counter)


def drop_universal_quantifiers(f: FolFormula) -> FolFormula:
    """Remove all ForAll wrappers; no Exists can remain (skolemize already removed every one).

    Remaining Variable occurrences are implicitly universally quantified -- the standard
    convention for clausal form, and the reason this step can just strip the wrapper rather than
    replace it with anything.
    """
    match f:
        case ForAll(_, body):
            return drop_universal_quantifiers(body)
        case Predicate():
            return f
        case FolNot(body):
            return FolNot(drop_universal_quantifiers(body))
        case FolAnd(items):
            return FolAnd(tuple(drop_universal_quantifiers(i) for i in items))
        case FolOr(items):
            return FolOr(tuple(drop_universal_quantifiers(i) for i in items))
    raise TypeError(f"not a FOL formula node (expected no Exists/Implies/Iff at this stage): {f!r}")


def _fol_parts(node: FolFormula, kind: type) -> tuple[FolFormula, ...]:
    """A node's operands if it is of `kind`, else the node itself as a single operand. Same
    "one level deep" contract as core.cnf._parts, for the same reason: by the time anything calls
    this, `distribute_and_over_or` has already flattened same-kind nesting away."""
    return node.items if isinstance(node, kind) else (node,)


class FolCNFExplosionError(RuntimeError):
    """Raised when CNF distribution would produce more than MAX_FOL_CLAUSES clauses.

    The Complexity & Scalability guard (HLD sections 18.3 step 6 and 18.11.2). A FOL formula,
    unlike the propositional grammar's flat output, can nest connectives and quantifiers deeply
    enough that distribution blows up exponentially -- this fails loudly and fast instead of
    letting one paragraph hang a request.
    """


def _distribute(f: FolFormula) -> FolFormula:
    """distribute_and_over_or's recursion. Mirrors core.cnf.distribute() exactly -- Predicate and
    FolNot(Predicate) are opaque leaves to this step, exactly as Atom and Not are to the
    propositional version, so no explicit case for them is needed beyond the final fallback."""
    match f:
        case FolAnd(items):
            parts = tuple(part for i in items for part in _fol_parts(_distribute(i), FolAnd))
            return FolAnd(parts) if len(parts) > 1 else parts[0]
        case FolOr(items):
            done = tuple(_distribute(i) for i in items)
            for index, item in enumerate(done):
                if isinstance(item, FolAnd):
                    rest = done[:index] + done[index + 1 :]
                    branches = tuple(FolOr((*rest, branch)) for branch in item.items)
                    return _distribute(FolAnd(branches))
            parts = tuple(part for i in done for part in _fol_parts(i, FolOr))
            return FolOr(parts) if len(parts) > 1 else parts[0]
    return f


def distribute_and_over_or(f: FolFormula) -> FolFormula:
    """Push Or under And until the formula is a conjunction of disjunctions (CNF).

    Raises FolCNFExplosionError if the TOP-LEVEL result would flatten (step 7) into more than
    MAX_FOL_CLAUSES clauses -- checked once here, not inside the recursion, so the guard counts
    the one true final clause count rather than an intermediate sub-formula's.
    """
    result = _distribute(f)
    clause_count = len(_fol_parts(result, FolAnd))
    if clause_count > MAX_FOL_CLAUSES:
        raise FolCNFExplosionError(
            f"CNF distribution produced {clause_count} clauses, over the MAX_FOL_CLAUSES limit "
            f"of {MAX_FOL_CLAUSES}"
        )
    return result


def _fol_literal(node: FolFormula) -> FolLiteral:
    match node:
        case Predicate():
            return (True, node)
        case FolNot(body) if isinstance(body, Predicate):
            return (False, body)
    raise TypeError(
        "not a literal (did distribute_and_over_or/drop_universal_quantifiers run first?): "
        f"{node!r}"
    )


def flatten_to_clauses(f: FolFormula) -> frozenset[FolClause]:
    """Convert a conjunction of disjunctions into a set of clauses.

    A top-level FolOr becomes one clause; a top-level Predicate or FolNot(Predicate) becomes one
    unit clause -- both covered by `_fol_parts`'s single-operand fallback, the same way a bare
    Atom is one clause in core.cnf.to_clauses().
    """
    return frozenset(
        frozenset(_fol_literal(literal) for literal in _fol_parts(disjunction, FolOr))
        for disjunction in _fol_parts(f, FolAnd)
    )


def _clause_key(clause: FolClause) -> tuple[str, ...]:
    """A deterministic sort key for one clause, so standardize_apart_clauses assigns clause
    indices in an order that cannot depend on frozenset/dict iteration (rule 4). `repr()` is
    exact and deterministic for these frozen dataclasses because every field is itself exact and
    deterministic -- it does not need to be human-readable, only stable."""
    return tuple(sorted(f"{polarity}{pred!r}" for polarity, pred in clause))


def _vars_in_term(term: Term) -> frozenset[str]:
    match term:
        case Variable(name):
            return frozenset({name})
        case Constant():
            return frozenset()
        case FunctionTerm(_, args):
            return frozenset().union(*(_vars_in_term(a) for a in args)) if args else frozenset()
    raise TypeError(f"not a term: {term!r}")


def standardize_apart_clauses(clauses: frozenset[FolClause]) -> frozenset[FolClause]:
    """Rename variables in each clause so they are globally unique across the whole set.

    Each clause is implicitly its own ForAll scope (HLD section 18.3 step 8): two clauses sharing
    a variable name "x" have INDEPENDENT x's, but the unifier cannot know that unless the names
    actually differ. A variable keeps its original name as a suffix ("c0_x") rather than being
    replaced outright, purely for readability in a proof trace -- it carries no meaning the
    unifier depends on.

    Clauses are processed in a fixed, sorted order (`_clause_key`) so which clause gets which
    index -- and so the renamed result -- cannot vary between runs (rule 4).
    """
    renamed = []
    for index, clause in enumerate(sorted(clauses, key=_clause_key)):
        names = frozenset().union(*(_vars_in_term(a) for _, pred in clause for a in pred.args))
        rename = {name: f"c{index}_{name}" for name in names}
        renamed.append(
            frozenset(
                (polarity, Predicate(pred.name, tuple(_rename_term(a, rename) for a in pred.args)))
                for polarity, pred in clause
            )
        )
    return frozenset(renamed)


def to_fol_clauses(formula: FolFormula) -> frozenset[FolClause]:
    """Run steps 1-7 on one formula and return its clause form.

    Deliberately stops at step 7, NOT step 8: standardize_apart_clauses must run once over the
    UNION of every premise's and the negated conclusion's clauses (HLD section 18.6, fol_prove
    step 3), not once per formula here -- otherwise two different premises could independently
    reuse the same per-formula variable names and this step's own job (telling them apart) would
    already be undone before fol_prove ever sees the combined set.
    """
    negation_normal = push_negation_inward(eliminate_iff_implies(formula))
    standardized = standardize_variables(negation_normal)
    skolemized = skolemize(standardized)
    quantifier_free = drop_universal_quantifiers(skolemized)
    cnf = distribute_and_over_or(quantifier_free)
    return flatten_to_clauses(cnf)
