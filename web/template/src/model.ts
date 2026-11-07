export type Scenario =
  | "monitoring"
  | "decision"
  | "contact"
  | "gap"
  | "stale"
  | "lost"
  | "recovery"
  | "exercise"
  | "truth";
export type CommandState =
  | "idle"
  | "review"
  | "pending"
  | "accepted"
  | "rejected"
  | "unconfirmed"
  | "declined"
  | "completed";
export type Selection = {
  kind: "usv" | "contact" | "segment";
  id: string;
} | null;
export const scenarios: { id: Scenario; label: string; description: string }[] =
  [
    {
      id: "monitoring",
      label: "Normal monitoring",
      description: "Routine cable watch. Five assets reporting.",
    },
    {
      id: "decision",
      label: "Route approval",
      description: "Review a held route change for USV-03.",
    },
    {
      id: "contact",
      label: "Camera-only contact",
      description: "C-024: no AIS correlation. Cue for a look.",
    },
    {
      id: "gap",
      label: "Coverage gap",
      description: "P-04 exceeds its target revisit interval.",
    },
    {
      id: "stale",
      label: "Single-USV stale",
      description: "USV-04 last reported 42 seconds ago.",
    },
    {
      id: "lost",
      label: "Feed lost",
      description: "Frozen observations. Operational controls locked.",
    },
    {
      id: "recovery",
      label: "Feed recovery",
      description: "Transport restored; operator must reconcile.",
    },
    {
      id: "exercise",
      label: "Link-cut exercise",
      description: "Simulated interruption of USV-04’s direct link.",
    },
    {
      id: "truth",
      label: "Evaluator / truth",
      description: "Separate truth-only annotations. Commands locked.",
    },
  ];
export const fleet = [
  {
    id: "01",
    role: "North patrol",
    mode: "PATROL",
    endurance: "06h 24m",
    battery: 78,
    returnBy: "20:45Z",
    link: "DIRECT",
    x: 424,
    y: 175,
    heading: 22,
    trend: "Stable draw",
  },
  {
    id: "02",
    role: "Cable watch",
    mode: "SENTINEL",
    endurance: "08h 12m",
    battery: 86,
    returnBy: "22:30Z",
    link: "DIRECT",
    x: 568,
    y: 285,
    heading: 106,
    trend: "Low draw",
  },
  {
    id: "03",
    role: "South patrol",
    mode: "PATROL",
    endurance: "04h 48m",
    battery: 62,
    returnBy: "19:15Z",
    link: "RELAYED",
    x: 388,
    y: 408,
    heading: 158,
    trend: "Stable draw",
  },
  {
    id: "04",
    role: "Comms relay",
    mode: "ECO",
    endurance: "05h 36m",
    battery: 69,
    returnBy: "20:00Z",
    link: "DIRECT",
    x: 605,
    y: 480,
    heading: 48,
    trend: "Low draw",
  },
  {
    id: "05",
    role: "Harbor reserve",
    mode: "DOCKED",
    endurance: "10h 05m",
    battery: 94,
    returnBy: "NOT REQUIRED",
    link: "DIRECT",
    x: 715,
    y: 555,
    heading: 270,
    trend: "Shore power",
  },
];
export const initialEvents = [
  {
    time: "14:32:08",
    source: "USV-03",
    category: "Coordination",
    text: "Route adjustment proposed · human approval held",
    ref: "03",
  },
  {
    time: "14:31:46",
    source: "USV-02",
    category: "Observation",
    text: "C-024 · camera observation, no AIS correlation",
    ref: "C-024",
  },
  {
    time: "14:30:22",
    source: "USV-01",
    category: "Coverage",
    text: "P-02 re-observed · visit age reset",
    ref: "P-02",
  },
  {
    time: "14:29:50",
    source: "SWARM",
    category: "Coordination",
    text: "USV-03 radio path established via USV-04",
    ref: "04",
  },
];
export const isLocked = (scenario: Scenario) =>
  ["lost", "recovery", "truth"].includes(scenario);
export const canSubmit = (scenario: Scenario, state: CommandState) =>
  !isLocked(scenario) &&
  (state === "idle" || state === "review" || state === "rejected");
