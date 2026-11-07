import { useEffect, useRef, useState } from "react";
import type { SceneMsg, Snapshot } from "../types";

import { FEED_POLL_MS, feedExpired } from "../freshness";
export { FEED_POLL_MS, FEED_STALE_MS, feedExpired } from "../freshness";

export const xy = (lon: number, lat: number): [number, number] => [
  Math.round((lon - 11) * 63212),
  Math.round((lat - 55.4) * 111190),
];
export function headingYaw(degrees: number) {
  return (-degrees * Math.PI) / 180;
}
export function viewerFeedUrl() {
  const supplied = new URLSearchParams(location.search).get("feed");
  const url = new URL(
    supplied ??
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.hostname || "127.0.0.1"}:8765/truth`,
  );
  if (!url.pathname.endsWith("/truth"))
    url.pathname = url.pathname.replace(/\/(shore)?$/, "") + "/truth";
  return url.toString();
}
export function useViewerFeed() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [scene, setScene] = useState<SceneMsg | null>(null);
  const [status, setStatus] = useState<"connecting" | "live" | "lost">(
    "connecting",
  );
  const [error, setError] = useState<string | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const received = useRef<number | null>(null);
  useEffect(() => {
    let stopped = false;
    let retry: number;
    const connect = () => {
      const ws = new WebSocket(viewerFeedUrl());
      socket.current = ws;
      ws.onmessage = (event) => {
        if (socket.current !== ws || stopped) return;
        try {
          const msg = JSON.parse(String(event.data));
          if (msg.type === "scene") setScene(msg);
          else if (msg.view === "truth" && Array.isArray(msg.boats)) {
            received.current = performance.now();
            setSnapshot(msg);
            setStatus("live");
          } else if (msg.type === "ack" && !msg.ok)
            setError(msg.error ?? "Command rejected");
        } catch {
          setError("Unrecognized feed message");
        }
      };
      ws.onclose = () => {
        if (!stopped) {
          setStatus("lost");
          retry = window.setTimeout(connect, 1200);
        }
      };
      ws.onerror = () => ws.close();
    };
    connect();
    const timer = window.setInterval(() => {
      if (received.current !== null && feedExpired(received.current, performance.now()))
        setStatus("lost");
    }, FEED_POLL_MS);
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      window.clearInterval(timer);
      socket.current?.close();
    };
  }, []);
  function command(cmd: object) {
    if (
      status !== "live" ||
      feedExpired(received.current, performance.now()) ||
      socket.current?.readyState !== WebSocket.OPEN
    ) {
      setError("Feed unavailable; command not sent");
      return;
    }
    setError(null);
    socket.current.send(JSON.stringify(cmd));
  }
  return { snapshot, scene, status, error, command };
}
