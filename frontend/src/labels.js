// The ONLY strings the frontend owns, and they are all furniture: button text, column headings,
// stage names. Nothing here is feedback, a verdict, a diagnosis or a hint -- every one of those
// arrives from the API, which renders it from `data/messages.yaml`.
//
// WHY A SEPARATE FILE. Two clients report the same outcomes. If the browser invented its own
// wording for a mistake, a student using the CLI and a student using the browser would be told
// different things about the same step and nothing would ever say so. The backend enforces this
// on its side (`test_adapters_hold_no_user_facing_wording`); this file is the frontend's half of
// the same discipline, and it is short on purpose -- if something belongs in messages.yaml it
// does not belong here.
export const UI = {
  title: "ProofPilot",
  subtitle: "Your pilot for learning to prove arguments, one step at a time.",

  stages: {
    facts: "Read & Facts",
    translate: "Translate",
    prove: "Prove",
    explain: "Explanation",
  },

  // Start screen
  startHeading: "Prove something",
  startSub:
    'Read an argument, check the facts it found, then build the proof step by step. If a step is wrong, ProofPilot explains why. An argument with a quantifier ("every", "some", "no") is checked by first-order resolution and given a verdict instead.',
  practiceTitle: "Practice",
  practiceBody:
    "A ready-made argument from the exercise bank. Good for a first look.",
  practiceButton: "Start practising",
  ownTitle: "Your own argument",
  ownBody:
    "Type any argument in plain English and ProofPilot checks whether the conclusion follows.",
  paragraphLabel: "Premises",
  paragraphPlaceholder: "If it rains then the match is cancelled. It rains.",
  conclusionLabel: "Conclusion",
  conclusionPlaceholder: "The match is cancelled.",
  ownButton: "Check this argument",
  ownRequired: "Write at least one premise sentence and a conclusion.",
  backToStart: "New argument",
  back: "← Back",

  // Read & Facts
  // HLD S18.7 Phase 8b: the propositional grammar (below) and the FOL grammar (the verdict
  // banner above this screen) are two INDEPENDENT readings of the same paragraph -- a sentence
  // can fail one and pass the other. Without this line, "Every human is mortal" tagged
  // QUANTIFIER_UNSUPPORTED right under a "Valid" FOL verdict reads as a contradiction.
  folModeNote:
    "This argument is being read as first-order logic; the list below is the simpler propositional reading, and its unsupported-quantifier notices don't apply to the proof above.",
  sentencesHeading: "The paragraph",
  conclusionHeading: "The claimed conclusion",
  factsHeading: "Facts the system extracted",
  factsHelp:
    "Check these before you prove anything. Every phrase grouped under one letter is being treated as the same fact.",
  mergeSame: "Same fact",
  mergeOpposite: "Opposites",
  mergeDifferent: "Different facts",
  mergeApply: "Apply",
  confirmFacts: "These facts are right — start proving",

  // the v2.7 A4 reset confirmation
  resetTitle: "This will discard your proof",
  resetConfirm: "Discard it and re-check the facts",
  resetCancel: "Keep my proof",

  // Prove
  boardHeading: "Clauses on the board",
  legendHeading: "What the letters mean",
  clauseEnglishHeading: "What each clause says",
  notNeeded: "not needed for this conclusion",
  resolventLabel: "The resolvent you get",
  resolventPlaceholder: "e.g. B  or  ~A B",
  insertHeading: "Insert",
  insertEmpty: "□  (empty clause)",
  submitStep: "Resolve",
  hint: "Hint",
  hintLevel: (n) => `Hint ${n} of 3`,
  claimNotProvable: "Does not follow",
  editFacts: "Edit facts",
  selectTwo: "Select two clauses to resolve.",

  notReachedProve: "You haven't reached Prove yet — confirm the facts first.",
  notReachedExplain: "You haven't finished the proof yet.",

  // Explanation
  proofHeading: "Your proof",
  fromSentence: "from",
  given: "given",
  goal: "negated conclusion",
  derived: "you derived",
  nextExercise: "Next exercise",
  conversionSteps: "How this became a clause",

  // FOL Prove board (HLD S18.16)
  folBoardHeading: "Clauses on the board",
  folResolventLabel: "The resolvent you get",
  folResolventPlaceholder:
    "e.g. PassTheExam(ravi)  or  ¬Study(ravi) ∨ PassTheExam(ravi)",

  // FOL Explanation (HLD S18.14, S18.15.6)
  derivationHeading: "How the first-order proof was derived",
  folClausesHeading: "The clauses",
  folStepsHeading: "Resolution steps",
  folTreeHeading: "Refutation tree",
  folConclusionHeading: "Conclusion",
  folOrigin: {
    premise: "premise",
    negated_goal: "negated goal",
    derived: "derived",
  },
  folUnifierLabel: "where",
  folNoUnifier: "no substitution needed",
  folNoProof: "No derivation to show — see the verdict above for why.",
  unrenderedTermsNote:
    "Terms written C1, C2… or f1(x), f2(x)… above are values the system had to introduce to prove this (Skolem terms) — they weren't in your original sentences.",

  // pilot mode only
  pilotIdLabel: "Pilot ID",
  pilotIdPlaceholder: "P1",
  pilotIdRequired: "Enter your Pilot ID above to start.",

  // chrome
  mastery: "Mastery",
  loading: "Working…",
  retry: "Try again",
  allDone: "Every skill is at the mastery threshold. Nothing left to practise.",
  offline: "Cannot reach the server. Is the backend running?",
};
