import { UI } from "./labels.js";

// Shows what the server said, and nothing of its own. `code` decides the colour; `message` is
// printed verbatim because it came from `data/messages.yaml`. A counterexample row is rendered
// as a small table because a row of truth values is a table, and reading it is the skill the
// does-not-follow exercises are teaching.
const TONE = {
  VALID: "good",
  CLAIM_ACCEPTED: "good",
  FACTS_CONFIRMED: "good",
  HINT_1: "hint",
  HINT_2: "hint",
  HINT_3: "hint",
  HINT_FALLBACK: "hint",
  HINT_NOT_FOLLOW_1: "hint",
  HINT_NOT_FOLLOW_2: "hint",
  HINT_NOT_FOLLOW_3: "hint",
};

export function Feedback({ feedback, problem }) {
  if (problem) {
    return (
      <p className="feedback bad" role="alert">
        <strong>{problem.code}</strong> {problem.message ?? UI.offline}
      </p>
    );
  }
  if (!feedback) return null;
  const row = feedback.extras?.counterexample;
  return (
    <div className={`feedback ${TONE[feedback.code] ?? "bad"}`} role="status">
      <p>
        <strong>{feedback.code}</strong> {feedback.message}
      </p>
      {row ? (
        <table className="row">
          <tbody>
            <tr>
              {Object.keys(row).map((symbol) => (
                <th key={symbol}>{symbol}</th>
              ))}
            </tr>
            <tr>
              {Object.values(row).map((value, index) => (
                <td key={index}>{value ? "T" : "F"}</td>
              ))}
            </tr>
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
