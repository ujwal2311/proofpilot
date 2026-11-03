import { forwardRef, useCallback, useLayoutEffect, useRef, useState } from "react";

import { UI } from "./labels.js";

// Turns the server's flat, indented tree lines ("  text  (F6)", 2 spaces per depth) into a
// nested structure so it can be drawn with real connector lines instead of read as plain text.
// The indentation is the only thing parsed -- the clause text and label are opaque strings,
// still entirely server-rendered (HLD S18.15.6 item 5); this file only lays them out differently.
function buildFolTree(lines) {
  const root = { children: [] };
  const stack = [{ depth: -1, node: root }];
  for (const line of lines) {
    const match = line.match(/^(\s*)(.*?)\s+\(([^()]+)\)\s*$/);
    if (!match) continue;
    const [, indent, text, label] = match;
    const depth = indent.length / 2;
    const node = { text, label, children: [] };
    while (stack.length > 1 && stack[stack.length - 1].depth >= depth) stack.pop();
    stack[stack.length - 1].node.children.push(node);
    stack.push({ depth, node });
  }
  return root.children[0] ?? null;
}

const CONNECTOR_HEIGHT = 34; // px: stem down from each box, the bar, the stem into the parent

// One clause box, its two antecedents (if any) drawn ABOVE it. The ref always lands on THIS
// node's own box (never the subtree wrapper) -- a parent measures its two children's box
// centers, never a lopsided subtree's overall bounding width, which is what kept the arrow and
// the box it points at drifting apart one level up whenever the two sides were uneven (found
// live: the empty clause ended up visibly right of its own arrow).
//
// `onSettled` is why a DEEPER merge (one whose own antecedent is itself a merge, not a leaf)
// stays aligned too. A node's `setGeometry` only SCHEDULES its own box's shift; the box has not
// actually moved in the DOM yet at that point. A parent that measured right then would capture
// the child's PRE-shift position -- found live, as drift that got worse the deeper a chain of
// merges went. Only calling `onSettled` from an effect keyed on `geometry` (so it fires AFTER
// that shift has committed) guarantees a parent never measures a child before it has settled.
export const FolTreeNode = forwardRef(function FolTreeNodeImpl(
  { node, originOf, onSettled },
  boxRef,
) {
  const containerRef = useRef(null);
  const leftBoxRef = useRef(null);
  const rightBoxRef = useRef(null);
  const [geometry, setGeometry] = useState(null); // {width, leftX, rightX} in container-local px
  const [left, right] = node.children;
  const hasPair = Boolean(left && right);

  const measure = useCallback(() => {
    const container = containerRef.current;
    const l = leftBoxRef.current;
    const r = rightBoxRef.current;
    if (!container || !l || !r) return;
    const base = container.getBoundingClientRect();
    const lr = l.getBoundingClientRect();
    const rr = r.getBoundingClientRect();
    setGeometry({
      width: base.width,
      leftX: lr.left + lr.width / 2 - base.left,
      rightX: rr.left + rr.width / 2 - base.left,
    });
  }, []);

  useLayoutEffect(() => {
    if (!hasPair) {
      onSettled?.();
      return undefined;
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [hasPair, measure, onSettled]);

  // Fires only once `geometry` has actually been committed (this node's own box has finished
  // moving to it) -- the signal a parent waits for before it measures THIS node.
  useLayoutEffect(() => {
    if (geometry) onSettled?.();
  }, [geometry, onSettled]);

  const isGoal = originOf[node.label] === "negated_goal";
  const isEmpty = node.text.startsWith("□");
  const midX = geometry ? (geometry.leftX + geometry.rightX) / 2 : null;
  const barY = CONNECTOR_HEIGHT - 10;

  return (
    <div
      className={`fol-tree-node${isGoal ? " goal" : ""}${isEmpty ? " empty" : ""}`}
      ref={containerRef}
    >
      {hasPair ? (
        <>
          <div className="fol-tree-pair">
            <div className="fol-tree-branch">
              <FolTreeNode node={left} originOf={originOf} ref={leftBoxRef} onSettled={measure} />
            </div>
            <div className="fol-tree-branch">
              <FolTreeNode
                node={right}
                originOf={originOf}
                ref={rightBoxRef}
                onSettled={measure}
              />
            </div>
          </div>
          {geometry ? (
            <svg
              className="fol-tree-connector"
              width={geometry.width}
              height={CONNECTOR_HEIGHT}
              viewBox={`0 0 ${geometry.width} ${CONNECTOR_HEIGHT}`}
              aria-hidden="true"
            >
              <line x1={geometry.leftX} y1="0" x2={geometry.leftX} y2={barY} className="fol-tree-line" />
              <line
                x1={geometry.rightX}
                y1="0"
                x2={geometry.rightX}
                y2={barY}
                className="fol-tree-line"
              />
              <line x1={geometry.leftX} y1={barY} x2={geometry.rightX} y2={barY} className="fol-tree-line" />
              <line x1={midX} y1={barY} x2={midX} y2={CONNECTOR_HEIGHT - 3} className="fol-tree-line" />
              <polygon
                points={`${midX - 5},${CONNECTOR_HEIGHT - 6} ${midX + 5},${CONNECTOR_HEIGHT - 6} ${midX},${CONNECTOR_HEIGHT}`}
                className="fol-tree-arrowhead"
              />
            </svg>
          ) : (
            <div className="fol-tree-connector" style={{ height: CONNECTOR_HEIGHT }} />
          )}
        </>
      ) : null}
      <div
        className="fol-tree-box"
        ref={boxRef}
        // Lands this box's own center on `midX` -- the SAME point the arrow above it points at
        // -- regardless of how wide its two antecedents' subtrees are relative to each other.
        style={midX != null ? { position: "relative", left: midX, transform: "translateX(-50%)" } : undefined}
      >
        <span className="literals">{node.text}</span>
        <span className="id">{node.label}</span>
      </div>
    </div>
  );
});

// The FOL-mode Explanation tab (HLD S18.14, S18.15.6) -- read-only, the system's own derivation,
// not the student's. Not a reuse of Explanation.jsx: that component is built around ClauseRec's
// string literals and `origin: "derived"` meaning the student clicked Resolve, neither of which
// exists here -- the whole proof is computed server-side at once. Same CSS classes so it reads as
// one system, not a second UI bolted on.
//
// EVERY field below comes from the server. The clause text, the origin tag, the negated-goal
// caption, the unifier, the conclusion sentence and the tree are all rendered by app/render.py
// from messages.yaml; this file only lays them out. The one thing it owns is furniture -- column
// headings and the word for an origin code -- exactly as labels.js's own contract requires.
export function FolExplanation({ folTrace, state, pending, onNext, onHome }) {
  const legend = folTrace?.legend ?? [];
  const steps = folTrace?.steps ?? [];
  const tree = folTrace?.tree ?? [];
  const treeRoot = tree.length ? buildFolTree(tree) : null;
  const originOf = Object.fromEntries(legend.map((entry) => [entry.label, entry.origin]));
  // A student who typed their own argument has no "next exercise" to go to -- sending them into
  // the practice bank is not what that button looks like it does.
  const ownQuestion = state?.mode === "own_question";

  return (
    <section>
      <h2>{UI.derivationHeading}</h2>

      {legend.length ? (
        <>
          <h3>{UI.folClausesHeading}</h3>
          <ol className="proof fol-legend">
            {legend.map((entry) => (
              <li key={entry.label} className={entry.origin === "negated_goal" ? "goal" : null}>
                <span className="id">{entry.label}</span>
                <span className="literals">{entry.text}</span>
                <span className="origin">{UI.folOrigin[entry.origin] ?? entry.origin}</span>
                {entry.note ? <span className="fol-note">{entry.note}</span> : null}
              </li>
            ))}
          </ol>
        </>
      ) : (
        <p className="help">{UI.folNoProof}</p>
      )}

      {steps.length ? (
        <>
          <h3>{UI.folStepsHeading}</h3>
          <ol className="proof fol-steps">
            {steps.map((step, index) => (
              <li key={index}>
                <span className="id">{index + 1}</span>
                <span className="literals">
                  {step.left} + {step.right} → {step.resolvent}
                  {/* The resolvent's own text, so a step is readable without scrolling back up
                      to the clause list to decode three labels. */}
                  <em className="fol-resolvent">{folTrace.clauses[step.resolvent]}</em>
                </span>
                <span className="origin">
                  {step.unifier ? `${UI.folUnifierLabel} ${step.unifier}` : UI.folNoUnifier}
                </span>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {treeRoot ? (
        <>
          <h3>{UI.folTreeHeading}</h3>
          {/* The server still sends indented plain text (HLD S18.15.6 item 5); `buildFolTree`
              above turns it into a real, precisely-connected diagram, no drawing library, no
              new dependency -- `FolTreeNode` measures actual rendered box positions via refs. */}
          <div className="fol-tree">
            <FolTreeNode node={treeRoot} originOf={originOf} />
          </div>
        </>
      ) : null}

      {folTrace?.conclusion ? (
        <>
          <h3>{UI.folConclusionHeading}</h3>
          <p className="fol-conclusion">{folTrace.conclusion}</p>
        </>
      ) : null}

      {folTrace?.has_unrendered_terms ? <p className="help">{UI.unrenderedTermsNote}</p> : null}

      <button
        type="button"
        className="primary"
        onClick={ownQuestion ? onHome : onNext}
        disabled={pending}
      >
        {ownQuestion ? UI.backToStart : UI.nextExercise}
      </button>
    </section>
  );
}
