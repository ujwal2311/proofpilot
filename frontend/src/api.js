// The only place the frontend talks to the server, and the only place it handles an error.
//
// The backend returns ONE error shape for everything -- `{code, message, details?}` -- including
// its own body validation and any unhandled exception (S4.1). So this file needs exactly one
// error path, and `message` is always a sentence that can be shown to a person: it comes from
// `data/messages.yaml`, never from here.
const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

// Pilot mode (HLD section 11, E5): off unless the env var is set, and even then the backend's
// own event log stays off unless PROOFPILOT_PILOT_LOG=1 is set server-side too -- this header is
// inert against a normal dev or CI backend. `pilotId` is a participant code (P1..P10), kept in
// sessionStorage (not localStorage: it should not outlive the browser tab) so a mid-session
// refresh does not silently stop attributing event-log lines to the right participant.
export const PILOT_MODE = import.meta.env.VITE_PILOT_MODE === "1";
const PILOT_ID_KEY = "proofpilot.pilot_id";

function loadPilotId() {
  try {
    return window.sessionStorage.getItem(PILOT_ID_KEY) ?? "";
  } catch {
    return "";
  }
}

let pilotId = PILOT_MODE ? loadPilotId() : "";
export const getPilotId = () => pilotId;
export const setPilotId = (id) => {
  pilotId = id;
  try {
    window.sessionStorage.setItem(PILOT_ID_KEY, id);
  } catch {
    // Best-effort only -- losing persistence is not worth failing the action over.
  }
};

// Thrown for every failure, so a caller has one thing to catch. `code` is what the UI branches
// on -- STATE_VERSION_MISMATCH triggers a reset -- and `message` is what it shows.
export class ApiError extends Error {
  constructor(code, message, details, status) {
    super(message);
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

async function post(path, body) {
  const headers = { "Content-Type": "application/json" };
  if (PILOT_MODE && pilotId) headers["X-Pilot-Id"] = pilotId;
  let answer;
  try {
    answer = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (cause) {
    // A network failure has no envelope to read, so it is the one message this file owns -- and
    // it is UI furniture ("is the backend running?"), not feedback about anyone's answer.
    throw new ApiError("OFFLINE", null, String(cause), 0);
  }
  const payload = await answer.json().catch(() => null);
  if (!answer.ok) {
    throw new ApiError(
      payload?.code ?? "INTERNAL_ERROR",
      payload?.message ?? null,
      payload?.details,
      answer.status,
    );
  }
  return payload;
}

export const api = {
  health: () => fetch(`${BASE}/api/health`).then((r) => r.json()),
  next: (state) => post("/api/next", state ? { state } : {}),
  parse: (paragraph, conclusion, merges = []) =>
    post("/api/parse", { paragraph, conclusion, merges }),
  act: (state, action) => post("/api/act", { state, action }),
};
