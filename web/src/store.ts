// Owner: C. One Zustand store: the WebSocket connection and the latest snapshot.
// N5: if no snapshot arrives for FEED_LOST_MS, the display is marked frozen (red banner).
// N6: the socket reconnects by itself; no page reload needed.
import { create } from "zustand";
import type { Ack, Command, SceneMsg, Snapshot } from "./types";

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
  setChannel: (c: Channel) => void;
  send: (c: Command) => boolean;
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
    if (msg.type === "snapshot") {
      useStore.setState({ snap: msg, conn: "live", lastMsgAt: performance.now() });
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
