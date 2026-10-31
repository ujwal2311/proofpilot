"""Unification: the Most General Unifier (MGU) of two terms, or two predicates.

See docs/HLD.md section 18.4. This module owns term unification and the occurs check only --
it knows nothing about clauses, polarity, or resolution (core.fol_resolve). It reads no files.

CONTRACT.
  occurs(var_name, term) -> bool            -- does var_name appear anywhere inside term.
  apply_subst(term, subst) -> Term          -- follow every binding, chains included.
  compose(s1, s2) -> Substitution           -- s1 then s2, composed; mutates neither.
  unify(t1, t2, subst=None) -> Substitution | None   -- MGU extending subst, or None on failure.
  unify_literals(lit1, lit2) -> Substitution | None  -- unify() on a complementary literal pair.

DELIBERATE WIDENING OF unify()'s TYPE, STATED HERE SO IT IS NOT MISTAKEN FOR A TYPO: HLD section
18.4.3 types `unify` as `(t1: Term, t2: Term, ...)` but then LISTS "Predicate vs Predicate: same
name, same arity -> unify args pairwise" among its own cases -- and section 18.4.4 describes
`unify_literals` only as returning "the MGU of the two predicates' argument lists", never
re-stating a name/arity check of its own. Read together, the name/arity/pairwise-unification
logic is meant to live ONCE, in `unify`, reused for both FunctionTerm and Predicate instead of
duplicated in `unify_literals` -- so `unify` is typed `Term | Predicate` here, and
`unify_literals` is a thin two-line wrapper that checks only polarity.
"""

from src.core.fol_models import (
    Constant,
    FolLiteral,
    FunctionTerm,
    Predicate,
    Substitution,
    Term,
    Variable,
)


def occurs(var_name: str, term: Term) -> bool:
    """True if `var_name` appears anywhere inside `term`.

    The occurs check: without it, unify(x, f(x)) would bind x -> f(x), and apply_subst would
    recurse forever chasing its own tail the first time anyone applied that binding.
    """
    match term:
        case Variable(name):
            return name == var_name
        case Constant():
            return False
        case FunctionTerm(_, args):
            return any(occurs(var_name, a) for a in args)
    raise TypeError(f"not a term: {term!r}")


def apply_subst(term: Term, subst: Substitution) -> Term:
    """Recursively replace every variable in `term` per `subst`, following chains: if x maps to
    y and y maps to c, applying to x gives c directly, not the intermediate y."""
    match term:
        case Variable(name):
            return apply_subst(subst[name], subst) if name in subst else term
        case Constant():
            return term
        case FunctionTerm(name, args):
            return FunctionTerm(name, tuple(apply_subst(a, subst) for a in args))
    raise TypeError(f"not a term: {term!r}")


def compose(s1: Substitution, s2: Substitution) -> Substitution:
    """A substitution equivalent to applying `s1` then `s2`. Mutates neither argument."""
    return {var: apply_subst(t, s2) for var, t in s1.items()} | s2


def _unify_pairwise(
    args1: tuple[Term, ...], args2: tuple[Term, ...], subst: Substitution
) -> Substitution | None:
    """Unify two equal-length argument tuples left to right, threading the substitution built so
    far into each next pair -- an earlier pair's binding must constrain a later one, e.g.
    unifying (x, x) against (a, b) must fail once x is already bound to a."""
    for a1, a2 in zip(args1, args2, strict=True):
        subst = unify(a1, a2, subst)
        if subst is None:
            return None
    return subst


def unify(
    t1: Term | Predicate, t2: Term | Predicate, subst: Substitution | None = None
) -> Substitution | None:
    """The MGU of `t1` and `t2` under the existing bindings `subst`, or None on failure.

    Both sides are chased through `subst` first (unless already a Predicate, which cannot itself
    be a substitution's value) so that a previously-bound variable is compared by what it is
    bound to, not by its bare name.
    """
    subst = {} if subst is None else subst
    chased1 = t1 if isinstance(t1, Predicate) else apply_subst(t1, subst)
    chased2 = t2 if isinstance(t2, Predicate) else apply_subst(t2, subst)
    match chased1, chased2:
        case Variable(n1), Variable(n2) if n1 == n2:
            return subst
        case Variable(name), _:
            return None if occurs(name, chased2) else subst | {name: chased2}
        case _, Variable(name):
            return None if occurs(name, chased1) else subst | {name: chased1}
        case Constant(a), Constant(b):
            return subst if a == b else None
        case FunctionTerm(n1, a1), FunctionTerm(n2, a2) if n1 == n2 and len(a1) == len(a2):
            return _unify_pairwise(a1, a2, subst)
        case Predicate(n1, a1), Predicate(n2, a2) if n1 == n2 and len(a1) == len(a2):
            return _unify_pairwise(a1, a2, subst)
    return None


def unify_literals(lit1: FolLiteral, lit2: FolLiteral) -> Substitution | None:
    """Unify two literals of OPPOSITE polarity -- the complementary pair a resolution step pivots
    on. Same-polarity pairs are rejected immediately, before any unification is attempted; a
    predicate-name or arity mismatch is rejected by `unify` itself (its Predicate/Predicate case
    guards on both), so there is nothing left for this function to check on its own.
    """
    polarity1, pred1 = lit1
    polarity2, pred2 = lit2
    if polarity1 == polarity2:
        return None
    return unify(pred1, pred2)
