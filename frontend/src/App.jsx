import { PILOT_MODE, setPilotId } from "./api.js";
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

  if (done) {
    return (
      <main>
        <Header />
        <p className="done">{UI.allDone}</p>
      </main>
    );
  }
  if (!state) {
    return (
      <main>
        <Header />
        {problem ? <Feedback problem={problem} /> : <p className="help">{UI.loading}</p>}
        {problem ? (
          <button type="button" onClick={restart}>
            {UI.retry}
          </button>
        ) : null}
      </main>
    );
  }

  const stage = state.stage === "read" ? "facts" : state.stage;
  return (
    <main aria-busy={pending}>
      <Header />
      <Stepper current={stage} />
      <MasteryBars mastery={state.mastery} />
      <Feedback feedback={feedback} problem={problem} />

      {stage === "facts" ? (
        <ReadFacts
          state={state}
          pending={pending}
          onMerge={(merge) =>
            parse(state.paragraph, state.conclusion, [...state.merges_applied, merge])
          }
          onConfirm={() => act({ type: "confirm_facts" })}
        />
      ) : null}

      {stage === "prove" ? (
        <ProveBoard
          state={state}
          pending={pending}
          onStep={(step) => act({ type: "step", ...step })}
          onHint={(level) => act({ type: "hint", level })}
          onClaim={() => act({ type: "claim_not_provable" })}
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

function Header() {
  return (
    <header>
      <h1>{UI.title}</h1>
      <p>{UI.subtitle}</p>
      {PILOT_MODE ? (
        <p>
          <label htmlFor="pilot-id">{UI.pilotIdLabel}</label>{" "}
          <input
            id="pilot-id"
            placeholder={UI.pilotIdPlaceholder}
            onChange={(event) => setPilotId(event.target.value.trim())}
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
