"""FOL resolution: every resolvent of two clauses, found by unifying one complementary pair.

See docs/HLD.md section 18.5. This module owns resolving two clauses and nothing else -- no
search (core.fol_search), no unification machinery of its own (core.unify), no file reads.

CONTRACT.
  apply_literal_subst(lit, subst) -> FolLiteral  -- substitution applied to a literal's terms.
  is_tautology_fol(clause) -> bool                -- a literal and its EXACT negation coexist.
  resolve(clause_a, clause_b) -> list[FolClause]  -- every non-tautological resolvent.
  canonical_literal(lit) -> str / canonical_clause(clause) -> tuple[str, ...]  -- stable sort keys.

SOUNDNESS, stated here because it is the one way to get this module quietly wrong: the MGU found
on the pivot pair is applied to EVERY surviving literal from BOTH parents, not only the ones that
came from whichever parent the pivot happened to sit in. Applying it selectively is the textbook
mistake that produces an unsound resolvent (HLD section 18.5's own warning).
"""

from src.core.fol_models import FolClause, FolLiteral, Predicate, Substitution
from src.core.unify import apply_subst, unify_literals


def apply_literal_subst(literal: FolLiteral, subst: Substitution) -> FolLiteral:
    """Apply a substitution to every term in a literal's predicate; polarity is untouched."""
    polarity, pred = literal
    return (polarity, Predicate(pred.name, tuple(apply_subst(a, subst) for a in pred.args)))


def is_tautology_fol(clause: FolClause) -> bool:
    """True if `clause` contains both (True, P(t)) and (False, P(t)) for the SAME t.

    "Same" means syntactically equal after whatever substitution already produced this clause --
    no further unification is attempted here (HLD section 18.5): two literals that could be made
    equal by binding a variable are not yet a tautology, only ones that already are one.
    """
    return any((not polarity, pred) in clause for polarity, pred in clause)


def resolve(clause_a: FolClause, clause_b: FolClause) -> list[FolClause]:
    """Every clause obtainable by resolving `clause_a` and `clause_b` on ONE complementary,
    unifiable literal pair. Resolving on two pairs at once is unsound (the propositional
    DOUBLE_CANCEL mistake) and is never attempted here, by construction: each iteration picks
    exactly one literal from each clause.

    Returns a plain list, not a deduplicated set -- HLD section 18.5 types it that way, and
    fol_search.py's BFS (Phase 7) already deduplicates states the same way core.search does, so
    deduplicating twice would be the needless kind of abstraction CLAUDE.md principle 4 rules out.
    """
    resolvents = []
    for pivot_a in clause_a:
        for pivot_b in clause_b:
            if pivot_a[0] == pivot_b[0]:
                continue
            mgu = unify_literals(pivot_a, pivot_b)
            if mgu is None:
                continue
            remaining = (clause_a - {pivot_a}) | (clause_b - {pivot_b})
            resolvent = frozenset(apply_literal_subst(lit, mgu) for lit in remaining)
            if not is_tautology_fol(resolvent):
                resolvents.append(resolvent)
    return resolvents


def canonical_literal(literal: FolLiteral) -> str:
    """Stable string representation for sorting -- same role as canonical() in logic.py. `repr`
    is exact and deterministic here because every field of a frozen dataclass term is itself
    exact and deterministic; it only needs to be stable, not human-readable."""
    polarity, pred = literal
    return f"{polarity}{pred!r}"


def canonical_clause(clause: FolClause) -> tuple[str, ...]:
    """Sort literals canonically inside a clause, so two equal clauses always print and compare
    the same way regardless of frozenset iteration order (rule 4)."""
    return tuple(sorted(canonical_literal(literal) for literal in clause))
