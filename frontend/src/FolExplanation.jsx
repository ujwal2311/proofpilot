import { UI } from "./labels.js";

// The FOL-mode Explanation tab (HLD S18.14, S18.15.6) -- read-only, the system's own derivation,
// not the student's. Not a reuse of Explanation.jsx: that component is built around ClauseRec's
// string literals and `origin: "derived"` meaning the student clicked Resolve, neither of which
// exists here -- the whole proof is computed server-side at once. Same CSS classes so it reads as
// one system, not a second UI bolted on.
//
// EVERY field below comes from the server. The clause text, the origin tag, the negated-goal
// caption, the unifier, the conclusion sentence and the tree are all rendered by app/render.py
// from messages.yaml; this file only lays them out. The one thing it owns is furniture -- column
// headings and the word for an origin code -- exactly as labels.js's own contract requires.
export function FolExplanation({ folTrace, state, pending, onNext, onHome }) {
  const legend = folTrace?.legend ?? [];
  const steps = folTrace?.steps ?? [];
  const tree = folTrace?.tree ?? [];
  // A student who typed their own argument has no "next exercise" to go to -- sending them into
  // the practice bank is not what that button looks like it does.
  const ownQuestion = state?.mode === "own_question";

  return (
    <section>
      <h2>{UI.derivationHeading}</h2>

      {legend.length ? (
        <>
          <h3>{UI.folClausesHeading}</h3>
          <ol className="proof fol-legend">
            {legend.map((entry) => (
              <li key={entry.label} className={entry.origin === "negated_goal" ? "goal" : null}>
                <span className="id">{entry.label}</span>
                <span className="literals">{entry.text}</span>
                <span className="origin">{UI.folOrigin[entry.origin] ?? entry.origin}</span>
                {entry.note ? <span className="fol-note">{entry.note}</span> : null}
              </li>
            ))}
          </ol>
        </>
      ) : (
        <p className="help">{UI.folNoProof}</p>
      )}

      {steps.length ? (
        <>
          <h3>{UI.folStepsHeading}</h3>
          <ol className="proof fol-steps">
            {steps.map((step, index) => (
              <li key={index}>
                <span className="id">{index + 1}</span>
                <span className="literals">
                  {step.left} + {step.right} → {step.resolvent}
                  {/* The resolvent's own text, so a step is readable without scrolling back up
                      to the clause list to decode three labels. */}
                  <em className="fol-resolvent">{folTrace.clauses[step.resolvent]}</em>
                </span>
                <span className="origin">
                  {step.unifier ? `${UI.folUnifierLabel} ${step.unifier}` : UI.folNoUnifier}
                </span>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {tree.length ? (
        <>
          <h3>{UI.folTreeHeading}</h3>
          {/* Pre-formatted on purpose: the server sends indented plain text (HLD S18.15.6 item
              5), and a <pre> is the whole renderer -- no drawing library, no new dependency. */}
          <pre className="fol-tree">{tree.join("\n")}</pre>
        </>
      ) : null}

      {folTrace?.conclusion ? (
        <>
          <h3>{UI.folConclusionHeading}</h3>
          <p className="fol-conclusion">{folTrace.conclusion}</p>
        </>
      ) : null}

      {folTrace?.has_unrendered_terms ? <p className="help">{UI.unrenderedTermsNote}</p> : null}

      <button
        type="button"
        className="primary"
        onClick={ownQuestion ? onHome : onNext}
        disabled={pending}
      >
        {ownQuestion ? UI.backToStart : UI.nextExercise}
      </button>
    </section>
  );
}
