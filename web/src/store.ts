// Owner: C. One Zustand store: the WebSocket connection and the latest snapshot.
// N5: if no snapshot arrives for FEED_LOST_MS, the display is marked frozen (red banner).
// N6: the socket reconnects by itself; no page reload needed.
import { create } from "zustand";
import { createHold, type Held } from "./undo";
import { OPERATOR_MODE, type Ack, type Command, type EvalData, type SceneMsg, type Scorecard, type Snapshot } from "./types";

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
  snap: Snapshot | null;
  lastMsgAt: number; // wall-clock ms of the last snapshot (UI timing only, never sim data)
  lastAck: Ack | null;
  selected: number | null; // boat highlighted on the chart and in the fleet panel
  select: (id: number | null) => void;
  selectedContact: string | null; // contact id, e.g. "contact:C-07"
  selectContact: (id: string | null) => void;
  hoverDecision: string | null; // decision card under the mouse: its ghost route is highlighted
  setHoverDecision: (id: string | null) => void;
  showComms: boolean; // feature 21 overlay toggle
  toggleComms: () => void;
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

export const useStore = create<State>((set, get) => ({
  channel: "shore",
  conn: "connecting",
  scene: null,
  snap: null,
  lastMsgAt: 0,
  lastAck: null,
  selected: null,
  select: (id) => set({ selected: id }),
  selectedContact: null,
  selectContact: (id) => set({ selectedContact: id }),
  hoverDecision: null,
  setHoverDecision: (id) => set({ hoverDecision: id }),
  showComms: true,
  toggleComms: () => set((s) => ({ showComms: !s.showComms })),
  held: null,
  answering: null,
  holdAnswer: (c, label) => hold.hold(c, label),
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
  evalOn: false,
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
    set({ channel: c, snap: null });
    connect();
  },
  send: (c) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
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
    const msg = JSON.parse(String(ev.data)) as Snapshot | SceneMsg | Ack;
    // Contract snapshots carry no "type"; anything with schema_version + boats is one.
    if (msg.type === "snapshot" || (msg.type === undefined && "boats" in msg)) {
      useStore.setState({ snap: msg as Snapshot, conn: "live", lastMsgAt: performance.now() });
    } else if (msg.type === "scene") {
      useStore.setState({ scene: msg });
    } else if (msg.type === "ack") {
      useStore.setState((st) => ({ lastAck: msg, answering: st.answering === msg.id ? null : st.answering }));
      if (!msg.ok) console.warn("command rejected:", msg.error);
    }
  };
  sock.onclose = () => {
    if (ws !== sock) return;
    useStore.setState({ conn: "lost" });
    retryTimer = window.setTimeout(connect, retryMs);
    retryMs = Math.min(retryMs * 2, 3000);
  };
}

// Watchdog: a socket can stay open while the sim stops sending. Data age decides, not the socket.
window.setInterval(() => {
  const s = useStore.getState();
  if (s.conn === "live" && performance.now() - s.lastMsgAt > FEED_LOST_MS) {
    useStore.setState({ conn: "lost" });
  }
}, 250);

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
    const ok = useStore.getState().send(c);
    if (ok && "id" in c) useStore.setState({ answering: c.id });
    return ok;
  },
  onChange: (h) => useStore.setState({ held: h }),
});
