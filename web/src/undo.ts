// Owner: C. Gap G2: a 5-second UNDO for Approve, Decline and Stop.
// The answer is held in the console and only leaves when the 5 s are up; UNDO (button or Esc)
// drops it and nothing is sent. Answers travel by radio and cannot be recalled once sent, so
// the hold has to happen here, before sending. One answer is held at a time.
import type { Command } from "./types";

export const HOLD_MS = 5000;

export interface Held { cmd: Command; label: string; until: number }

export interface HoldDeps {
  send: (c: Command) => boolean;
  onChange: (h: Held | null) => void;
  now?: () => number;
  setTimer?: (fn: () => void, ms: number) => unknown;
  clearTimer?: (t: unknown) => void;
  holdMs?: number;
}

export function createHold(deps: HoldDeps) {
  const now = deps.now ?? (() => Date.now());
  const setTimer = deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
  const clearTimer = deps.clearTimer ?? ((t) => clearTimeout(t as ReturnType<typeof setTimeout>));
  const holdMs = deps.holdMs ?? HOLD_MS;
  let held: Held | null = null;
  let timer: unknown = null;

  const set = (h: Held | null) => { held = h; deps.onChange(h); };

  return {
    /** Hold a command; false if another one is already held (one at a time). */
    hold(cmd: Command, label: string): boolean {
      if (held) return false;
      set({ cmd, label, until: now() + holdMs });
      timer = setTimer(() => {
        const h = held;
        timer = null;
        set(null);
        if (h) deps.send(h.cmd);
      }, holdMs);
      return true;
    },
    /** Drop the held command; nothing is sent. False if nothing was held. */
    undo(): boolean {
      if (!held) return false;
      clearTimer(timer);
      timer = null;
      set(null);
      return true;
    },
    current: (): Held | null => held,
  };
}
