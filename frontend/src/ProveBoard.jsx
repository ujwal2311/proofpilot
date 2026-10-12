import { useState } from "react";

import { UI } from "./labels.js";

// The Prove stage. Clause cards, a resolvent input with insert buttons, the three hint levels and
// "Does not follow".
//
// NOTHING IS DECIDED HERE. The student picks two clauses and types a resolvent; the server says
// whether it is valid, which mistake it is, and whether it shortened the proof. The board is
// re-rendered from the session the server returns, so the only state this component owns is what
// the student has selected and typed.
//
// Irrelevant clauses are MARKED, never hidden (section 6.5). The filter reports what the
// conclusion cannot reach; the student may still use any clause, and noticing which premises are
// not needed is part of what the long exercises teach.
export function ProveBoard({ state, pending, onStep, onHint, onClaim, onEditFacts }) {
  const [picked, setPicked] = useState([]);
  const [resolvent, setResolvent] = useState("");

  const toggle = (id) =>
    setPicked((current) =>
      current.includes(id)
        ? current.filter((other) => other !== id)
        : [...current.slice(-1), id],
    );

  const symbols = [
    ...new Set(state.clauses.flatMap((clause) => clause.literals.map((l) => l.replace("~", "")))),
  ].sort();

  const ready = picked.length === 2 && !pending;
  const submit = () => {
    onStep({ clause_a: picked[0], clause_b: picked[1], resolvent: resolvent.trim().split(/\s+/).filter(Boolean) });
    setPicked([]);
    setResolvent("");
  };

  return (
    <section>
      <h2>{UI.boardHeading}</h2>
      <ul className="board">
        {state.clauses.map((clause) => {
          const relevant = state.relevant_ids.includes(clause.id);
          return (
            <li key={clause.id}>
              <button
                type="button"
                className={`clause ${picked.includes(clause.id) ? "picked" : ""} ${relevant ? "" : "dim"}`}
                onClick={() => toggle(clause.id)}
                disabled={pending}
                aria-pressed={picked.includes(clause.id)}
              >
                <span className="id">{clause.id}</span>
                <span className="literals">
                  {clause.literals.length ? clause.literals.join(" ∨ ") : "□"}
                </span>
                {relevant ? null : <span className="note">{UI.notNeeded}</span>}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="step">
        <label htmlFor="resolvent">{UI.resolventLabel}</label>
        <input
          id="resolvent"
          value={resolvent}
          placeholder={UI.resolventPlaceholder}
          onChange={(event) => setResolvent(event.target.value)}
          disabled={pending}
        />
        <div className="insert" aria-label={UI.insertHeading}>
          <span>{UI.insertHeading}</span>
          {symbols.map((symbol) => (
            <span key={symbol}>
              <button type="button" onClick={() => setResolvent((r) => `${r} ${symbol}`.trim())} disabled={pending}>
                {symbol}
              </button>
              <button type="button" onClick={() => setResolvent((r) => `${r} ~${symbol}`.trim())} disabled={pending}>
                ~{symbol}
              </button>
            </span>
          ))}
          {/* The empty clause is the GOAL of a refutation, so it gets its own button rather than
              being something a student has to know to express by leaving the box blank. */}
          <button type="button" onClick={() => setResolvent("")} disabled={pending}>
            {UI.insertEmpty}
          </button>
        </div>
        <button type="button" className="primary" onClick={submit} disabled={!ready}>
          {UI.submitStep}
        </button>
        {picked.length === 2 ? null : <p className="help">{UI.selectTwo}</p>}
      </div>

      <div className="actions">
        {[1, 2, 3].map((level) => (
          <button
            key={level}
            type="button"
            onClick={() => onHint(level)}
            disabled={pending || level > state.hint_level + 1}
            title={UI.hintLevel(level)}
          >
            {UI.hint} {level}
          </button>
        ))}
        <button type="button" onClick={onClaim} disabled={pending}>
          {UI.claimNotProvable}
        </button>
        <button type="button" onClick={onEditFacts} disabled={pending}>
          {UI.editFacts}
        </button>
      </div>
    </section>
  );
}
