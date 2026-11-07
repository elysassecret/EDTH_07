// Owner: C. One Zustand store: the WebSocket connection and the latest snapshot.
// N5: if no snapshot arrives for FEED_LOST_MS, the display is marked frozen (red banner).
// N6: the socket reconnects by itself; no page reload needed.
import { create } from "zustand";
import { createHold, type Held } from "./undo";
import { actionsFor, decisionRevision } from "./console-model";
import { EVALUATOR_MODE, OPERATOR_MODE, type Ack, type Command, type EvalData, type SceneMsg, type Scorecard, type Snapshot } from "./types";

const FEED_LOST_MS = 2000;

export type Channel = "shore" | "truth";
export type ConnState = "connecting" | "live" | "lost";
export type Display = "day" | "dusk" | "night";
export type Panel = "inject" | "evidence" | "help" | "menu" | null;

function loadDisplay(): Display {
  try {
    const v = localStorage.getItem("display");
    return v === "day" || v === "night" ? v : "dusk";
  } catch {
    return "dusk";
  }
}

interface State {
  channel: Channel;
  conn: ConnState;
  scene: SceneMsg | null;
  snap: Snapshot | null; // what the console shows: the live picture, or a replay frame
  live: Snapshot | null; // the newest live picture (always kept, also while replaying)
  replayT: number | null; // sim s of the replay frame on screen; null = live
  showReplay: (frame: Snapshot | null) => void; // null = back to live
  replayPlaying: boolean; // playing the recording forward (the live run is not affected)
  replaySpeed: number; // playback warp, 0.25-999 (sim seconds per real second)
  setReplayPlaying: (on: boolean) => void;
  setReplaySpeed: (v: number) => void;
  lastMsgAt: number; // wall-clock ms of the last snapshot (UI timing only, never sim data)
  lastAck: Ack | null;
  commandError: string | null; // local transport feedback, never a fabricated server ACK
  selected: number | null; // boat highlighted on the chart and in the fleet panel
  select: (id: number | null) => void;
  selectedSegment: string | null;
  selectSegment: (id: string | null) => void;
  selectedContact: string | null; // contact id, e.g. "contact:C-07"
  selectContact: (id: string | null) => void;
  hoverDecision: string | null; // decision card under the mouse: its ghost route is highlighted
  setHoverDecision: (id: string | null) => void;
  showComms: boolean; // feature 21 overlay toggle
  toggleComms: () => void;
  showRings: boolean; // #88 sensor rings toggle
  toggleRings: () => void;
  // Evaluator view: a second socket to /truth, open only while this is on. Off by default,
  // never available in operator mode (?operator).
  held: Held | null; // G2: an answer waiting out its 5 s UNDO window
  answering: string | null; // decision id of an answer that has left, until its ack
  holdAnswer: (c: Command, label: string) => boolean;
  undoAnswer: () => boolean;
  panel: Panel; // the one open side panel; Esc closes it (U5)
  setPanel: (p: Panel) => void;
  display: Display; // U4 day / dusk / night (feature 33)
  setDisplay: (d: Display) => void;
  digestOpen: boolean; // U2 "since you last looked"
  lastLookT: number | null; // sim time of the officer's last look (null = not yet)
  setDigest: (open: boolean, lookedAt?: number) => void;
  placing: { ais: boolean } | null; // exercise: next chart click places a synthetic contact
  setPlacing: (p: { ais: boolean } | null) => void;
  evalOn: boolean;
  evalData: EvalData | null;
  scorecard: Scorecard | null;
  toggleEval: () => void;
  setChannel: (c: Channel) => void;
  send: (c: Command) => boolean;
}

/** HTTP URL on the same server as the feed (incident report, tamper demo). */
export function apiUrl(path: string): string {
  return `${feedUrl("shore").replace(/\/shore$/, "").replace(/^ws/, "http")}${path}`;
}

function feedUrl(channel: Channel): string {
  const q = new URLSearchParams(window.location.search).get("feed");
  const base = q ?? `ws://${window.location.hostname || "localhost"}:8765`;
  return `${base.replace(/\/$/, "")}/${channel}`;
}

let ws: WebSocket | null = null;
let retryMs = 500;
let retryTimer: number | undefined;
let queuedRevision: string | null = null;

export const useStore = create<State>((set, get) => ({
  channel: "shore",
  conn: "connecting",
  scene: null,
  snap: null,
  live: null,
  replayT: null,
  showReplay: (frame) =>
    set((s) => (frame ? { snap: frame, replayT: frame.t } : { snap: s.live, replayT: null, replayPlaying: false })),
  replayPlaying: false,
  replaySpeed: 60,
  setReplayPlaying: (on) => set({ replayPlaying: on }),
  setReplaySpeed: (v) => set({ replaySpeed: Math.min(999, Math.max(0.25, v)) }),
  lastMsgAt: 0,
  lastAck: null,
  commandError: null,
  selected: null,
  select: (id) => set({ selected: id, selectedContact: null, selectedSegment: null }),
  selectedSegment: null,
  selectSegment: (id) => set({ selectedSegment: id, selected: null, selectedContact: null }),
  selectedContact: null,
  selectContact: (id) => set({ selectedContact: id, selected: null, selectedSegment: null }),
  hoverDecision: null,
  setHoverDecision: (id) => set({ hoverDecision: id }),
  showComms: true,
  toggleComms: () => set((s) => ({ showComms: !s.showComms })),
  showRings: true,
  toggleRings: () => set((s) => ({ showRings: !s.showRings })),
  held: null,
  answering: null,
  holdAnswer: (c, label) => {
    const state = get();
    if (state.conn !== "live" || state.channel !== "shore" || state.answering || state.held || !state.snap || !("id" in c)) return false;
    const decision = state.snap.decisions.find((d) => d.id === c.id);
    if (!decision || decision.state !== "pending" || !actionsFor(decision).some((action) => action === c.cmd)) return false;
    queuedRevision = decisionRevision(decision, state.snap);
    set({ commandError: null });
    return hold.hold(c, label);
  },
  undoAnswer: () => hold.undo(),
  panel: null,
  setPanel: (p) => set((s) => ({ panel: s.panel === p ? null : p })),
  display: loadDisplay(),
  setDisplay: (d) => {
    try { localStorage.setItem("display", d); } catch { /* private window: not remembered */ }
    set({ display: d });
  },
  digestOpen: false,
  lastLookT: null,
  setDigest: (open, lookedAt) => set((s) => ({ digestOpen: open, lastLookT: lookedAt ?? s.lastLookT })),
  placing: null,
  setPlacing: (p) => set({ placing: p }),
  evalOn: EVALUATOR_MODE, // ?evaluator turns the comparison on at load (#88)
  evalData: null,
  scorecard: null,
  toggleEval: () => {
    const on = !get().evalOn && !OPERATOR_MODE;
    set({ evalOn: on, evalData: null });
    if (on) connectEval();
    else disconnectEval();
  },
  setChannel: (c) => {
    if (c === get().channel) return;
    if (c === "truth" && OPERATOR_MODE) return;
    if (hold.undo()) set({ commandError: "Queued answer cancelled before switching views; nothing was transmitted." });
    set({ channel: c, snap: null, live: null, replayT: null, conn: "connecting", selected: null, selectedContact: null, selectedSegment: null, placing: null });
    connect();
  },
  send: (c) => {
    // Recheck age at dispatch too: a throttled watchdog must not allow stale commands.
    if (get().conn === "live" && performance.now() - get().lastMsgAt > FEED_LOST_MS) loseFeed();
    if (!ws || ws.readyState !== WebSocket.OPEN || get().conn !== "live") {
      set({ commandError: "Not sent: fresh feed unavailable." });
      return false;
    }
    if (get().replayT !== null && !["pause", "speed", "reset"].includes(c.cmd)) {
      set({ commandError: "Not sent: you are watching a replay. Press Live to act on the live picture." });
      return false;
    }
    if (["confirm", "stop", "approve", "decline", "ack", "escalate"].includes(c.cmd) && get().channel !== "shore") {
      set({ commandError: "Not sent: evaluator view is read-only for operator decisions." });
      return false;
    }
    set({ commandError: null });
    ws.send(JSON.stringify(c));
    return true;
  },
}));

export function connect(): void {
  window.clearTimeout(retryTimer);
  if (ws) {
    ws.onclose = null;
    ws.close();
  }
  const sock = new WebSocket(feedUrl(useStore.getState().channel));
  ws = sock;
  sock.onopen = () => {
    retryMs = 500;
  };
  sock.onmessage = (ev) => {
    if (ws !== sock) return; // an old channel must never overwrite the new picture
    let msg: Snapshot | SceneMsg | Ack;
    try { msg = JSON.parse(String(ev.data)) as Snapshot | SceneMsg | Ack; }
    catch { return; }
    if (!msg || typeof msg !== "object") return;
    // Contract snapshots carry no "type"; anything with schema_version + boats is one.
    if (msg.type === "snapshot" || (msg.type === undefined && "boats" in msg)) {
      const incoming = msg as Snapshot;
      const state = useStore.getState();
      if (incoming.view !== state.channel) return;
      const prev = state.live ?? state.snap;
      const reset = prev && (incoming.t < prev.t || incoming.seed !== prev.seed);
      const cancelled = reset ? hold.undo() : false;
      const answered = state.answering && incoming.decisions.some((d) => d.id === state.answering && d.state !== "pending");
      // while replaying, the live picture keeps arriving but the screen stays on the replay
      // frame; a reset of the run ends the replay (its recording starts again)
      const replaying = state.replayT !== null && !reset;
      useStore.setState({ live: incoming, conn: "live", lastMsgAt: performance.now(),
        ...(replaying ? {} : { snap: incoming, replayT: null }),
        ...(reset || answered ? { answering: null } : {}),
        ...(cancelled ? { commandError: "Queued answer cancelled on simulation reset; nothing was transmitted." } : {}),
      });
    } else if (msg.type === "scene") {
      useStore.setState({ scene: msg });
    } else if (msg.type === "ack") {
      useStore.setState((st) => ({ lastAck: msg, answering: st.answering === msg.id ? null : st.answering }));
      if (!msg.ok) console.warn("command rejected:", msg.error);
    }
  };
  sock.onclose = () => {
    if (ws !== sock) return;
    loseFeed();
    retryTimer = window.setTimeout(connect, retryMs);
    retryMs = Math.min(retryMs * 2, 3000);
  };
}

// Watchdog: a socket can stay open while the sim stops sending. Data age decides, not the socket.
window.setInterval(() => {
  const s = useStore.getState();
  if (s.conn === "live" && performance.now() - s.lastMsgAt > FEED_LOST_MS) {
    loseFeed();
  }
}, 250);

function loseFeed(): void {
  const cancelled = hold.undo();
  // An in-flight answer is unconfirmed, not permission to block unrelated tasks forever.
  useStore.setState({ conn: "lost", answering: null, ...(cancelled ? {
    commandError: "Queued answer cancelled on feed loss; nothing was transmitted.",
  } : {}) });
}

// ---- evaluator socket (/truth), separate from the operator's channel
let evalWs: WebSocket | null = null;
let evalTimer: number | undefined;

function connectEval(): void {
  window.clearTimeout(evalTimer);
  disconnectEval();
  const sock = new WebSocket(feedUrl("truth"));
  evalWs = sock;
  sock.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data)) as { eval?: EvalData; scorecard?: Scorecard };
    if (msg.eval && useStore.getState().evalOn) {
      useStore.setState({ evalData: msg.eval, scorecard: msg.scorecard ?? null });
    }
  };
  sock.onclose = () => {
    if (evalWs !== sock) return;
    useStore.setState({ evalData: null });
    if (useStore.getState().evalOn) evalTimer = window.setTimeout(connectEval, 1000);
  };
}

function disconnectEval(): void {
  window.clearTimeout(evalTimer);
  if (evalWs) {
    evalWs.onclose = null;
    evalWs.close();
    evalWs = null;
  }
}

// G2: answers wait 5 s before they leave the console (src/undo.ts)
const hold = createHold({
  send: (c) => {
    const state = useStore.getState();
    const decision = "id" in c ? state.snap?.decisions.find((d) => d.id === c.id) : null;
    if (state.conn !== "live" || state.channel !== "shore" || !state.snap || !decision || decision.state !== "pending" || decisionRevision(decision, state.snap) !== queuedRevision) {
      useStore.setState({ commandError: "Queued answer cancelled: feed, view or task changed before transmission." });
      return false;
    }
    const ok = state.send(c);
    if (ok && "id" in c) useStore.setState({ answering: c.id });
    return ok;
  },
  onChange: (h) => useStore.setState({ held: h }),
});

// ?evaluator: the comparison starts on, so open its /truth socket now (after the store exists).
if (EVALUATOR_MODE) connectEval();
