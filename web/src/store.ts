// Owner: C. One Zustand store: the WebSocket connection and the latest snapshot.
// N5: if no snapshot arrives for FEED_LOST_MS, the display is marked frozen (red banner).
// N6: the socket reconnects by itself; no page reload needed.
import { create } from "zustand";
import { OPERATOR_MODE, type Ack, type Command, type EvalData, type SceneMsg, type Scorecard, type Snapshot } from "./types";

const FEED_LOST_MS = 2000;

export type Channel = "shore" | "truth";
export type ConnState = "connecting" | "live" | "lost";

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
      useStore.setState({ lastAck: msg });
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
