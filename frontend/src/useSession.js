// The one piece of state the app has, and the one place a request is made.
//
// Every action goes through `run`, which does three things no component should repeat: it sets a
// pending flag so buttons can disable (no double submit), it catches the single error shape, and
// it persists the session. A component that called `api` directly would have to remember all
// three, and the one that forgot would be the one a student found.
//
// There is NO logic here. The session comes back from the server already updated -- mastery
// moved, clause added, hint charged -- and this only stores it. The frontend never computes a
// verdict, a diagnosis or an evidence update.
import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "./api.js";
import * as storage from "./storage.js";

export function useSession() {
  const [state, setState] = useState(null);
  const [feedback, setFeedback] = useState(null); // {code, message, extras} from the last action
  const [problem, setProblem] = useState(null); // an ApiError the student should see
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [started, setStarted] = useState(false); // has the student chosen practice or own-question yet
  const [warnings, setWarnings] = useState([]);
  const [folMessage, setFolMessage] = useState(null); // rendered text, or null (HLD S18.7 Phase 8b)
  const [clauseEnglish, setClauseEnglish] = useState({}); // {clause id: rendered phrase text}

  const run = useCallback(async (work, { keepFeedback = false } = {}) => {
    setPending(true);
    setProblem(null);
    if (!keepFeedback) setFeedback(null);
    try {
      return await work();
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      // A saved session from an older build is not an error the student caused, and there is
      // nothing for them to decide: drop it and start clean. The server's own sentence explains
      // what happened, so it is shown rather than swallowed.
      if (error.code === "STATE_VERSION_MISMATCH" || error.code === "UNKNOWN_FIELD") {
        storage.clear();
        setState(null);
      }
      setProblem(error);
      return null;
    } finally {
      setPending(false);
    }
  }, []);

  const keep = useCallback((next) => {
    setState(next);
    if (next) storage.save(next);
    return next;
  }, []);

  const nextExercise = useCallback(
    (from = null) =>
      run(async () => {
        setStarted(true);
        const answer = await api.next(from);
        setDone(answer.done);
        setClauseEnglish(answer.clause_english ?? {});
        keep(answer.state);
        return answer;
      }),
    [run, keep],
  );

  const parse = useCallback(
    (paragraph, conclusion, merges = []) =>
      run(async () => {
        setStarted(true);
        const answer = await api.parse(paragraph, conclusion, merges);
        setWarnings(answer.warnings ?? []);
        setFolMessage(answer.fol_message ?? null);
        setClauseEnglish(answer.clause_english ?? {});
        return keep(answer.state);
      }),
    [run, keep],
  );

  const act = useCallback(
    (action) =>
      run(async () => {
        const answer = await api.act(state, action);
        setFeedback({ code: answer.code, message: answer.message, extras: answer.extras });
        setClauseEnglish(answer.clause_english ?? {});
        keep(answer.state);
        return answer;
      }, { keepFeedback: true }),
    [run, keep, state],
  );

  // Restore on first load. A stored session that the server rejects is handled by `run` above,
  // which clears it -- so a bad save cannot wedge the app. A FRESH visitor sees the start screen
  // (practice vs. your own argument) rather than being dropped straight into a random exercise --
  // that choice belongs to the student, not to whichever one happened to load first.
  useEffect(() => {
    const saved = storage.load();
    if (saved) {
      setState(saved);
      setStarted(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restart = useCallback(() => {
    storage.clear();
    setState(null);
    setFeedback(null);
    nextExercise();
  }, [nextExercise]);

  // Back to the start screen -- NOT the same as `restart`, which jumps straight into practice.
  const goHome = useCallback(() => {
    storage.clear();
    setState(null);
    setFeedback(null);
    setWarnings([]);
    setFolMessage(null);
    setClauseEnglish({});
    setStarted(false);
  }, []);

  return {
    state,
    feedback,
    problem,
    pending,
    done,
    started,
    warnings,
    folMessage,
    clauseEnglish,
    nextExercise,
    parse,
    act,
    restart,
    goHome,
    setState,
  };
}
