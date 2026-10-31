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
  subtitle: "step-level feedback for propositional logic — plus a first-order verdict for quantified arguments",

  stages: { facts: "Read & Facts", translate: "Translate", prove: "Prove", explain: "Explanation" },

  // Start screen
  startHeading: "Prove something",
  startSub:
    "Read an argument, check the facts it found, then build the proof yourself — ProofPilot tells you exactly where a step goes wrong instead of just marking it wrong. An argument using a quantifier (\"every\", \"some\", \"no\") is checked directly by first-order resolution and shown a verdict instead.",
  practiceTitle: "Practice",
  practiceBody: "A ready-made argument from the exercise bank. Good for a first look.",
  practiceButton: "Start practising",
  ownTitle: "Your own argument",
  ownBody: "Type any argument in plain English and ProofPilot checks whether the conclusion follows.",
  paragraphLabel: "Premises",
  paragraphPlaceholder:
    "If it rains then the match is cancelled. It rains.",
  conclusionLabel: "Conclusion",
  conclusionPlaceholder: "The match is cancelled.",
  ownButton: "Check this argument",
  ownRequired: "Write at least one premise sentence and a conclusion.",
  backToStart: "New argument",
  back: "← Back",

  // Read & Facts
  sentencesHeading: "The paragraph",
  conclusionHeading: "The claimed conclusion",
  factsHeading: "Facts the system extracted",
  factsHelp: "Check these before you prove anything. Every phrase grouped under one letter is being treated as the same fact.",
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
