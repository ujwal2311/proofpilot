import { useState } from "react";

import { UI } from "./labels.js";

// The FOL Prove stage (HLD S18.16). Reuses propositional ProveBoard's own interaction pattern --
// a two-clause picker, a resolvent text input, a hint button -- deliberately, not a new layout:
// a student who already knows the propositional board should not have to re-learn the UI to
// practise the logic. The literal-insert buttons are the FOL-granularity equivalent of
// propositional's per-symbol insert buttons; the difference is what they insert (a clause's own
// literal text, not a bare letter), not the pattern.
//
// NOTHING IS DECIDED HERE. Validity, the mistake code and the message all come from the server
// (`fol_step`). The only thing this component owns is the student's OWN accepted-clause list --
// lifted to `useSession` (HLD S18.16.8), not the server -- which it appends to on a VALID
// response and sends back, unmodified, so the next step can reference a clause the student
// derived two steps ago.
export function FolProveBoard({
  folTrace,
  accepted,
  onAcceptedStep,
  pending,
  onStep,
  onHint,
  onClaim,
}) {
  const [picked, setPicked] = useState([]);
  const [resolvent, setResolvent] = useState("");

  // The full legend includes the ENGINE'S OWN solution path (derived clauses from its minimal
  // derivation) -- fine for the read-only Explanation tab, but showing them here would hand the
  // student the answer before they have done anything (found live, 2026-11-02: the board
  // initially displayed F4/F5 pre-labeled with the exact clauses that finish the proof). Only
  // premises and the negated goal are shown; a clause the STUDENT derives is added once they
  // derive it. Numbering still continues from the FULL legend length, matching the server's own
  // `_fol_board_labels` exactly -- the gap this leaves in the visible sequence is honest, not a
  // bug: those labels are real, just not shown yet.
  const legend = folTrace?.legend ?? [];
  const inputs = legend
    .filter((entry) => entry.origin !== "derived")
    .map((entry) => ({ label: entry.label, text: entry.text }));
  const derived = accepted.map((text, index) => ({
    label: `F${legend.length + index + 1}`,
    text,
  }));
  const board = [...inputs, ...derived];

  const toggle = (label) =>
    setPicked((current) =>
      current.includes(label)
        ? current.filter((other) => other !== label)
        : [...current.slice(-1), label],
    );

  // Every literal appearing in either PICKED clause -- the FOL equivalent of propositional's
  // per-symbol insert row, built from the two clauses actually in play rather than the whole
  // board, since a literal from an unrelated clause is never useful to insert here.
  const pickedTexts = board
    .filter((entry) => picked.includes(entry.label))
    .map((entry) => entry.text);
  const literals = [
    ...new Set(pickedTexts.flatMap((text) => text.split(" ∨ "))),
  ].filter((literal) => literal !== "□ (empty clause)");

  const ready = picked.length === 2 && !pending;
  const submit = () => {
    onStep({
      clause_a: picked[0],
      clause_b: picked[1],
      resolvent,
      accepted,
    }).then((result) => {
      if (result?.code === "VALID") onAcceptedStep(resolvent);
    });
    setPicked([]);
    setResolvent("");
  };

  return (
    <section className="prove-layout">
      <div className="board-main">
        <h2>{UI.folBoardHeading}</h2>
        <ul className="board">
          {board.map((entry) => (
            <li key={entry.label}>
              <button
                type="button"
                className={`clause ${picked.includes(entry.label) ? "picked" : ""}`}
                onClick={() => toggle(entry.label)}
                disabled={pending}
                aria-pressed={picked.includes(entry.label)}
              >
                <span className="id">{entry.label}</span>
                <span className="literals">{entry.text}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="step">
          <label htmlFor="fol-resolvent">{UI.folResolventLabel}</label>
          <input
            id="fol-resolvent"
            value={resolvent}
            placeholder={UI.folResolventPlaceholder}
            onChange={(event) => setResolvent(event.target.value)}
            disabled={pending}
          />
          <div className="insert" aria-label={UI.insertHeading}>
            <span>{UI.insertHeading}</span>
            {literals.map((literal) => (
              <button
                key={literal}
                type="button"
                onClick={() =>
                  setResolvent((r) => (r ? `${r} ∨ ${literal}` : literal))
                }
                disabled={pending}
              >
                {literal}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setResolvent("")}
              disabled={pending}
            >
              {UI.insertEmpty}
            </button>
          </div>
          <button
            type="button"
            className="primary"
            onClick={submit}
            disabled={!ready}
          >
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
              disabled={pending}
            >
              {UI.hint} {level}
            </button>
          ))}
          <button type="button" onClick={onClaim} disabled={pending}>
            {UI.claimNotProvable}
          </button>
        </div>
      </div>
    </section>
  );
}
