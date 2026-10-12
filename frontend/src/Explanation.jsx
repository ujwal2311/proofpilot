import { UI } from "./labels.js";

// The M1 Explanation panel: a structured summary of the finished proof, built from the clause
// trace the session already carries. `origin` and `source_sentence_id` are on every clause for
// exactly this -- so the panel can say where each one came from without re-deriving anything.
//
// M2 replaces the structure with prose from `narrate.py` (S7). What is here is the M1 version the
// milestone promises, not a placeholder.
const ORIGIN = { given: UI.given, goal: UI.goal, derived: UI.derived };

export function Explanation({ state, pending, onNext }) {
  return (
    <section>
      <h2>{UI.proofHeading}</h2>
      <ol className="proof">
        {state.clauses.map((clause) => (
          <li key={clause.id} className={clause.origin}>
            <span className="id">{clause.id}</span>
            <span className="literals">
              {clause.literals.length ? clause.literals.join(" ∨ ") : "□"}
            </span>
            <span className="origin">
              {ORIGIN[clause.origin]}
              {clause.source_sentence_id ? ` ${UI.fromSentence} ${clause.source_sentence_id}` : ""}
            </span>
          </li>
        ))}
      </ol>
      <button type="button" className="primary" onClick={onNext} disabled={pending}>
        {UI.nextExercise}
      </button>
    </section>
  );
}
