// localStorage, which can fail for reasons that have nothing to do with this app: private
// browsing, a full quota, a policy that blocks it. Every call is wrapped, and a failure degrades
// to "no saved session" rather than taking the page down -- losing a session is a small loss and
// a blank screen is a total one.
const KEY = "proofpilot.session";

// Saved as an envelope, not a bare State: the FOL verdict and trace are computed once by
// /api/parse and never recomputed, so a reload that restored only the State left the page
// claiming a proof it could no longer show (2026-11-02 fresh-eyes pass).
export function save(state, fol = null) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ state, fol }));
  } catch {
    // Nothing to do and nothing worth telling the student: the session still works in memory,
    // it just will not survive a reload.
  }
}

export function load() {
  try {
    const text = window.localStorage.getItem(KEY);
    const saved = text ? JSON.parse(text) : null;
    // A bare-State save from an older build has no `state` key. It is not readable as an
    // envelope, so it is dropped the same way an unparseable one is.
    return saved && saved.state ? saved : null;
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
