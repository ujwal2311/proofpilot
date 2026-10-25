import { useEffect, useState } from "react";

import { PILOT_MODE, getPilotId, setPilotId } from "./api.js";
import { Explanation } from "./Explanation.jsx";
import { Feedback } from "./Feedback.jsx";
import { MasteryBars } from "./MasteryBars.jsx";
import { ProveBoard } from "./ProveBoard.jsx";
import { ReadFacts } from "./ReadFacts.jsx";
import { StartScreen } from "./StartScreen.jsx";
import { UI } from "./labels.js";
import { useSession } from "./useSession.js";

// Stage routing and nothing else. The STAGE COMES FROM THE SESSION -- the server decides it, via
// `tutor.TRANSITIONS` -- so this component reads `state.stage` rather than keeping a copy. A
// client-side stage would be a second opinion about what may happen next, and the transition
// table exists precisely so there is only one.
const STAGES = ["read", "facts", "translate", "prove", "explain"];
const STAGE_ORDER = ["facts", "translate", "prove", "explain"];

export default function App() {
  const {
    state,
    feedback,
    problem,
    pending,
    done,
    started,
    warnings,
    clauseEnglish,
    nextExercise,
    parse,
    act,
    restart,
    goHome,
  } = useSession();
  const [pilotId, setPilotIdState] = useState(() => getPilotId());
  const [editingFacts, setEditingFacts] = useState(false);

  // What the student is LOOKING AT, independent of where the session actually is. Clicking a tab
  // only ever changes this -- never state.stage, never the API. A genuine stage advance (e.g.
  // confirming facts) re-syncs the view to follow it, same as before this existed.
  const stage = state ? (state.stage === "read" ? "facts" : state.stage) : null;
  const [activeTab, setActiveTab] = useState(stage);
  useEffect(() => {
    if (stage) setActiveTab(stage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

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

  // Pilot mode needs a participant code before any action reaches the server -- checked before
  // the start screen too, since practice/own-question both post to the server immediately.
  if (PILOT_MODE && !pilotId.trim()) {
    return (
      <main>
        <Header pilotId={pilotId} onPilotId={updatePilotId} />
        <p className="help">{UI.pilotIdRequired}</p>
      </main>
    );
  }

  if (!state) {
    return (
      <main>
        <Header pilotId={pilotId} onPilotId={updatePilotId} />
        {problem ? <Feedback problem={problem} /> : null}
        {problem && started ? (
          <button type="button" onClick={restart}>
            {UI.retry}
          </button>
        ) : (
          <StartScreen pending={pending} onPractice={nextExercise} onOwnQuestion={parse} />
        )}
      </main>
    );
  }

  const showEditableFacts =
    (stage === "facts" && activeTab === "facts") || (stage === "prove" && editingFacts);
  const reached = (tab) => STAGE_ORDER.indexOf(stage) >= STAGE_ORDER.indexOf(tab);
  const selectTab = (tab) => {
    setEditingFacts(false); // clicking any tab abandons "just looking", not a merge
    setActiveTab(tab);
  };

  return (
    <main aria-busy={pending}>
      <Header pilotId={pilotId} onPilotId={updatePilotId} />
      <div className="toolbar">
        <Stepper current={showEditableFacts ? "facts" : activeTab} onSelect={selectTab} />
        <button type="button" className="ghost" onClick={goHome} disabled={pending}>
          {UI.backToStart}
        </button>
      </div>
      <MasteryBars mastery={state.mastery} />
      {warnings.length ? (
        <ul className="warnings">
          {warnings.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      ) : null}
      <Feedback feedback={feedback} problem={problem} />

      {showEditableFacts ? (
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

      {!showEditableFacts && activeTab === "facts" ? <ReadFacts state={state} readOnly /> : null}

      {!showEditableFacts && activeTab === "prove" ? (
        reached("prove") ? (
          <ProveBoard
            state={state}
            pending={pending}
            clauseEnglish={clauseEnglish}
            onStep={(step) => act({ type: "step", ...step })}
            onHint={(level) => act({ type: "hint", level })}
            onClaim={() => act({ type: "claim_not_provable" })}
            onEditFacts={() => setEditingFacts(true)}
          />
        ) : (
          <NotReachedYet text={UI.notReachedProve} />
        )
      ) : null}

      {!showEditableFacts && activeTab === "explain" ? (
        reached("explain") ? (
          <Explanation state={state} pending={pending} onNext={() => nextExercise(state)} />
        ) : (
          <NotReachedYet text={UI.notReachedExplain} />
        )
      ) : null}

      {pending ? (
        <p className="pending" role="status">
          {UI.loading}
        </p>
      ) : null}
    </main>
  );
}

function NotReachedYet({ text }) {
  return (
    <section className="not-reached">
      <p>{text}</p>
    </section>
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

// What the student is looking at, and the ones they have passed. Clicking a tab only ever calls
// `onSelect` -- it never reaches the API, so browsing a past or future stage is never an action.
// M1 has no Translate stage, so it is shown only when the session actually reaches it rather than
// as a permanent empty promise.
function Stepper({ current, onSelect }) {
  const shown = STAGES.filter((stage) => stage !== "read" && (stage !== "translate" || current === "translate"));
  return (
    <nav className="stepper" aria-label="stages">
      <ol>
        {shown.map((stage) => (
          <li key={stage}>
            <button
              type="button"
              className={stage === current ? "here" : ""}
              aria-current={stage === current ? "step" : undefined}
              onClick={() => onSelect(stage)}
            >
              {UI.stages[stage]}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
