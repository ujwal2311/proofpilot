import { useState } from "react";

import { PILOT_MODE, getPilotId, setPilotId } from "./api.js";
import { Explanation } from "./Explanation.jsx";
import { Feedback } from "./Feedback.jsx";
import { MasteryBars } from "./MasteryBars.jsx";
import { ProveBoard } from "./ProveBoard.jsx";
import { ReadFacts } from "./ReadFacts.jsx";
import { UI } from "./labels.js";
import { useSession } from "./useSession.js";

// Stage routing and nothing else. The STAGE COMES FROM THE SESSION -- the server decides it, via
// `tutor.TRANSITIONS` -- so this component reads `state.stage` rather than keeping a copy. A
// client-side stage would be a second opinion about what may happen next, and the transition
// table exists precisely so there is only one.
const STAGES = ["read", "facts", "translate", "prove", "explain"];

export default function App() {
  const { state, feedback, problem, pending, done, nextExercise, parse, act, restart } =
    useSession();
  const [pilotId, setPilotIdState] = useState(() => getPilotId());
  const [editingFacts, setEditingFacts] = useState(false);

  const updatePilotId = (value) => {
    setPilotIdState(value);
    setPilotId(value);
  };

  if (done) {
    return (
      <main>
        <Header pilotId={pilotId} onPilotId={updatePilotId} />
        <p className="done">{UI.allDone}</p>
      </main>
    );
  }
  if (!state) {
    return (
      <main>
        <Header pilotId={pilotId} onPilotId={updatePilotId} />
        {problem ? <Feedback problem={problem} /> : <p className="help">{UI.loading}</p>}
        {problem ? (
          <button type="button" onClick={restart}>
            {UI.retry}
          </button>
        ) : null}
      </main>
    );
  }

  // Pilot mode needs a participant code before any action reaches the server -- the server's own
  // event log refuses a request with none (api/main.py's `_require_pilot_id`), so blocking here
  // is a courtesy that turns a 400 into a plain on-screen ask instead.
  if (PILOT_MODE && !pilotId.trim()) {
    return (
      <main>
        <Header pilotId={pilotId} onPilotId={updatePilotId} />
        <p className="help">{UI.pilotIdRequired}</p>
      </main>
    );
  }

  const stage = state.stage === "read" ? "facts" : state.stage;
  const showFacts = stage === "facts" || (stage === "prove" && editingFacts);
  return (
    <main aria-busy={pending}>
      <Header pilotId={pilotId} onPilotId={updatePilotId} />
      <Stepper current={stage} />
      <MasteryBars mastery={state.mastery} />
      <Feedback feedback={feedback} problem={problem} />

      {showFacts ? (
        <ReadFacts
          state={state}
          pending={pending}
          onMerge={(merge) => {
            const merges = [...state.merges_applied, merge];
            if (stage === "prove") {
              act({ type: "merge", merges }).then((result) => {
                if (result) setEditingFacts(false);
              });
            } else {
              parse(state.paragraph, state.conclusion, merges);
            }
          }}
          onConfirm={() =>
            stage === "prove" ? setEditingFacts(false) : act({ type: "confirm_facts" })
          }
        />
      ) : null}

      {stage === "prove" && !editingFacts ? (
        <ProveBoard
          state={state}
          pending={pending}
          onStep={(step) => act({ type: "step", ...step })}
          onHint={(level) => act({ type: "hint", level })}
          onClaim={() => act({ type: "claim_not_provable" })}
          onEditFacts={() => setEditingFacts(true)}
        />
      ) : null}

      {stage === "explain" ? (
        <Explanation state={state} pending={pending} onNext={() => nextExercise(state)} />
      ) : null}

      {pending ? (
        <p className="pending" role="status">
          {UI.loading}
        </p>
      ) : null}
    </main>
  );
}

function Header({ pilotId, onPilotId }) {
  return (
    <header>
      <h1>{UI.title}</h1>
      <p>{UI.subtitle}</p>
      {PILOT_MODE ? (
        <p>
          <label htmlFor="pilot-id">{UI.pilotIdLabel}</label>{" "}
          <input
            id="pilot-id"
            value={pilotId}
            placeholder={UI.pilotIdPlaceholder}
            onChange={(event) => onPilotId(event.target.value.trim())}
          />
        </p>
      ) : null}
    </header>
  );
}

// The stage the student is on, and the ones they have passed. M1 has no Translate stage, so it is
// shown only when the session actually reaches it rather than as a permanent empty promise.
function Stepper({ current }) {
  const shown = STAGES.filter((stage) => stage !== "read" && (stage !== "translate" || current === "translate"));
  return (
    <nav className="stepper" aria-label="stages">
      <ol>
        {shown.map((stage) => (
          <li key={stage} className={stage === current ? "here" : ""} aria-current={stage === current ? "step" : undefined}>
            {UI.stages[stage]}
          </li>
        ))}
      </ol>
    </nav>
  );
}
