import { useState } from "react";

import { UI } from "./labels.js";

// Read & Facts. Two jobs: show what the parser made of each sentence, and let the student correct
// the fact grouping before any proving starts.
//
// EVERY PHRASE is shown under its symbol, not just the first (v2.6 A1). An automatic merge the
// student disagrees with is invisible otherwise -- they would see one phrase, assume it is the
// only one, and prove something about a fact that silently absorbed another.
//
// Merges are addressed by PHRASE ID (v2.7 A3). Quoting the text back breaks the moment a student
// edits a sentence, and two sentences can produce the same phrase.
export function ReadFacts({ state, pending, onMerge, onConfirm, readOnly = false }) {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [relation, setRelation] = useState("same");
  const [confirming, setConfirming] = useState(null);

  const phrases = state.facts.flatMap((fact) =>
    fact.phrases.map(([id, text]) => ({ id, text, symbol: fact.symbol })),
  );
  const ready = a && b && a !== b && !pending;

  // The v2.7 A4 reset. Symbols are re-assigned from scratch on every merge, so a proof built on
  // the old assignment is no longer ABOUT the same propositions -- it has to go. The student
  // confirms first, because they cannot see what is at risk.
  const wouldDiscard = state.clauses.some((clause) => clause.origin === "derived");
  const apply = () => {
    const merge = { a, b, relation };
    if (wouldDiscard) setConfirming(merge);
    else onMerge(merge);
  };

  return (
    <section>
      <h2>{UI.sentencesHeading}</h2>
      <ol className="sentences">
        {state.sentences.slice(0, -1).map((sentence) => (
          <li key={sentence.id} className={sentence.status}>
            {sentence.text}
            {sentence.error_code ? <code> {sentence.error_code}</code> : null}
          </li>
        ))}
      </ol>
      <h2>{UI.conclusionHeading}</h2>
      <p className="conclusion">{state.sentences.at(-1)?.text}</p>

      <h2>{UI.factsHeading}</h2>
      <p className="help">{UI.factsHelp}</p>
      <ul className="facts">
        {state.facts.map((fact) => (
          <li key={fact.symbol}>
            <span className="symbol">{fact.symbol}</span>
            <span className="phrases">
              {fact.phrases.map(([id, text]) => (
                <span key={id} className="phrase">
                  <code>{id}</code> {text}
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>

      {readOnly ? null : (
        <>
          <fieldset className="merge" disabled={pending}>
            <legend>{UI.mergeApply}</legend>
            <select value={a} onChange={(event) => setA(event.target.value)} aria-label="first phrase">
              <option value="">—</option>
              {phrases.map((phrase) => (
                <option key={phrase.id} value={phrase.id}>
                  {phrase.id}: {phrase.text}
                </option>
              ))}
            </select>
            <select
              value={relation}
              onChange={(event) => setRelation(event.target.value)}
              aria-label="relation"
            >
              <option value="same">{UI.mergeSame}</option>
              <option value="opposite">{UI.mergeOpposite}</option>
              <option value="different">{UI.mergeDifferent}</option>
            </select>
            <select value={b} onChange={(event) => setB(event.target.value)} aria-label="second phrase">
              <option value="">—</option>
              {phrases.map((phrase) => (
                <option key={phrase.id} value={phrase.id}>
                  {phrase.id}: {phrase.text}
                </option>
              ))}
            </select>
            <button type="button" onClick={apply} disabled={!ready}>
              {UI.mergeApply}
            </button>
          </fieldset>

          {confirming ? (
            <div className="confirm" role="alertdialog" aria-label={UI.resetTitle}>
              <p>
                <strong>{UI.resetTitle}</strong>
              </p>
              <button
                type="button"
                onClick={() => {
                  onMerge(confirming);
                  setConfirming(null);
                }}
              >
                {UI.resetConfirm}
              </button>
              <button type="button" onClick={() => setConfirming(null)}>
                {UI.resetCancel}
              </button>
            </div>
          ) : null}

          <button type="button" className="primary" onClick={onConfirm} disabled={pending}>
            {UI.confirmFacts}
          </button>
        </>
      )}
    </section>
  );
}
