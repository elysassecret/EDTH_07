// Owner: C. U5 keyboard shortcuts, for a watch officer in gloves in a dim room.
// Decision keys (A approve, D decline, S stop, C confirm) live in the decision dock.
// Here: Space acknowledges the top alert, 1-5 focus a boat, Esc closes, ? shows the help.
// Keys are ignored while typing in a field and when a modifier key is held.
import { useEffect } from "react";
import { useStore } from "../store";
import { sortedAlerts } from "./AlertPanel";

export function isTyping(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null;
  return !!el && (["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName) || el.isContentEditable);
}

export function Shortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e)) return;
      const st = useStore.getState();
      if (e.key === " ") {
        const top = st.snap ? sortedAlerts(st.snap.alerts).find((a) => !a.ack) : undefined;
        if (top && st.conn === "live") {
          e.preventDefault();
          st.send({ cmd: "ack", id: top.id });
          st.setDigest(true);
        }
      } else if (/^[1-9]$/.test(e.key)) {
        const id = Number(e.key);
        if (st.snap?.boats.some((b) => b.id === id)) st.select(st.selected === id ? null : id);
      } else if (e.key === "Escape") {
        if (st.panel) st.setPanel(st.panel);
        st.setPlacing(null);
        if (st.digestOpen) st.setDigest(false, st.snap?.t);
        st.select(null);
      } else if (e.key === "?" || (e.code === "Slash" && e.shiftKey)) {
        st.setPanel("help");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return null;
}

const KEYS: [string, string][] = [
  ["A", "Approve the decision in the dock"],
  ["D", "Decline it"],
  ["C", "Confirm a running decision"],
  ["S", "Stop a running decision"],
  ["Space", "Acknowledge the top alert"],
  ["1 – 5", "Focus that USV (press again to clear)"],
  ["Esc", "Close a panel, cancel placing, clear focus"],
  ["?", "This help"],
];

export function HelpOverlay() {
  const setPanel = useStore((s) => s.setPanel);
  return (
    <div className="help" role="dialog" aria-label="Keyboard shortcuts">
      <div className="inject-head">Keyboard shortcuts<button className="close" onClick={() => setPanel(null)} aria-label="Close">×</button></div>
      <table><tbody>{KEYS.map(([k, w]) => <tr key={k}><td><kbd>{k}</kbd></td><td>{w}</td></tr>)}</tbody></table>
      <div className="muted small">Keys do nothing while you type in a field.</div>
    </div>
  );
}
