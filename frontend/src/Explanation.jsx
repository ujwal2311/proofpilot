import { UI } from "./labels.js";

// The M1 Explanation panel: a structured summary of the finished proof, built from the clause
// trace the session already carries. `origin` and `source_sentence_id` are on every clause for
// exactly this -- so the panel can say where each one came from without re-deriving anything.
//
// M2 replaces the structure with prose from `narrate.py` (S7). What is here is the M1 version the
// milestone promises, not a placeholder.
const ORIGIN = { given: UI.given, goal: UI.goal, derived: UI.derived };

// A given clause's trace is keyed by the sentence that produced it (`source_sentence_id`); the
// goal clause has none of its own (it is the NEGATED conclusion, not a premise), so it reads the
// conclusion's trace instead -- the conclusion is always the last sentence (`session.analyse`).
function sentenceIdFor(clause, state) {
  return clause.origin === "goal" ? state.sentences.at(-1)?.id : clause.source_sentence_id;
}

export function Explanation({ state, pending, onNext }) {
  return (
    <section>
      <h2>{UI.proofHeading}</h2>
      <ol className="proof">
        {state.clauses.map((clause) => {
          const steps = state.conversions[sentenceIdFor(clause, state)];
          return (
            <li key={clause.id} className={clause.origin}>
              <span className="id">{clause.id}</span>
              <span className="literals">
                {clause.literals.length ? clause.literals.join(" ∨ ") : "□"}
              </span>
              <span className="origin">
                {ORIGIN[clause.origin]}
                {clause.source_sentence_id
                  ? ` ${UI.fromSentence} ${clause.source_sentence_id}`
                  : ""}
              </span>
              {steps?.length ? (
                <details className="conversion">
                  <summary>{UI.conversionSteps}</summary>
                  <ol>
                    {steps.map((step, index) => (
                      <li key={index}>
                        <strong>{step.law}</strong>: {step.before} → {step.after}
                      </li>
                    ))}
                  </ol>
                </details>
              ) : null}
            </li>
          );
        })}
      </ol>
      <button type="button" className="primary" onClick={onNext} disabled={pending}>
        {UI.nextExercise}
      </button>
    </section>
  );
}
