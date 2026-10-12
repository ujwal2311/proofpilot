// localStorage, which can fail for reasons that have nothing to do with this app: private
// browsing, a full quota, a policy that blocks it. Every call is wrapped, and a failure degrades
// to "no saved session" rather than taking the page down -- losing a session is a small loss and
// a blank screen is a total one.
const KEY = "proofpilot.session";

export function save(state) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Nothing to do and nothing worth telling the student: the session still works in memory,
    // it just will not survive a reload.
  }
}

export function load() {
  try {
    const text = window.localStorage.getItem(KEY);
    return text ? JSON.parse(text) : null;
  } catch {
    // Unparseable means it was written by a different build, or corrupted. Either way it is not
    // a session this version can use, so it is dropped rather than repaired.
    clear();
    return null;
  }
}

export function clear() {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* see save() */
  }
}
