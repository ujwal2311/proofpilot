import { useState } from "react";

import { UI } from "./labels.js";

// The front door. Two equally real ways in -- a ready-made exercise, or the student's own
// argument -- rather than dropping every visitor straight into practice mode. Posts through
// `onOwnQuestion`, which is `useSession`'s `parse()`: the SAME /api/parse the merge-reset path
// already uses, so there is no second code path for "a paragraph the student typed."
export function StartScreen({ pending, onPractice, onOwnQuestion }) {
  const [paragraph, setParagraph] = useState("");
  const [conclusion, setConclusion] = useState("");
  const ready = paragraph.trim() && conclusion.trim() && !pending;

  const submit = (event) => {
    event.preventDefault();
    if (ready) onOwnQuestion(paragraph.trim(), conclusion.trim());
  };

  return (
    <section className="start">
      <h2 className="start-heading">{UI.startHeading}</h2>
      <p className="start-sub">{UI.startSub}</p>

      <div className="start-cards">
        <div className="card">
          <h3>{UI.practiceTitle}</h3>
          <p>{UI.practiceBody}</p>
          <button type="button" className="primary" onClick={() => onPractice()} disabled={pending}>
            {UI.practiceButton}
          </button>
        </div>

        <div className="card card-own">
          <h3>{UI.ownTitle}</h3>
          <p>{UI.ownBody}</p>
          <form onSubmit={submit}>
            <label htmlFor="own-paragraph">{UI.paragraphLabel}</label>
            <textarea
              id="own-paragraph"
              rows={4}
              value={paragraph}
              placeholder={UI.paragraphPlaceholder}
              onChange={(event) => setParagraph(event.target.value)}
              disabled={pending}
            />
            <label htmlFor="own-conclusion">{UI.conclusionLabel}</label>
            <input
              id="own-conclusion"
              value={conclusion}
              placeholder={UI.conclusionPlaceholder}
              onChange={(event) => setConclusion(event.target.value)}
              disabled={pending}
            />
            <button type="submit" className="primary" disabled={!ready}>
              {UI.ownButton}
            </button>
            {!ready && (paragraph || conclusion) && !pending ? (
              <p className="help">{UI.ownRequired}</p>
            ) : null}
          </form>
        </div>
      </div>
    </section>
  );
}
