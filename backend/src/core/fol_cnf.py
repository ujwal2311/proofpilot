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

from src.core.fol_models import (
    Constant,
    Exists,
    FolAnd,
    FolFormula,
    FolIff,
    FolImplies,
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
