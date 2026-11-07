import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createHold, HOLD_MS, type Held } from "./undo";
import type { Command } from "./types";

describe("5-second undo (G2)", () => {
  let sent: Command[];
  let changes: (Held | null)[];
  const approve: Command = { cmd: "approve", id: "close:contact:C-07" };
  const make = () => createHold({ send: (c) => { sent.push(c); return true; }, onChange: (h) => changes.push(h) });

  beforeEach(() => { vi.useFakeTimers(); sent = []; changes = []; });
  afterEach(() => { vi.useRealTimers(); });

  it("sends only after the hold", () => {
    const h = make();
    expect(h.hold(approve, "Approve")).toBe(true);
    vi.advanceTimersByTime(HOLD_MS - 1);
    expect(sent).toEqual([]);
    expect(h.current()?.label).toBe("Approve");
    vi.advanceTimersByTime(1);
    expect(sent).toEqual([approve]);
    expect(h.current()).toBeNull();
  });

  it("undo sends nothing", () => {
    const h = make();
    h.hold(approve, "Approve");
    vi.advanceTimersByTime(3000);
    expect(h.undo()).toBe(true);
    vi.advanceTimersByTime(10_000);
    expect(sent).toEqual([]);
    expect(changes.at(-1)).toBeNull();
    expect(h.undo()).toBe(false);
  });

  it("holds one answer at a time", () => {
    const h = make();
    expect(h.hold(approve, "Approve")).toBe(true);
    expect(h.hold({ cmd: "decline", id: "close:contact:C-07" }, "Decline")).toBe(false);
    vi.advanceTimersByTime(HOLD_MS);
    expect(sent).toEqual([approve]);
    expect(h.hold({ cmd: "stop", id: "contact:C-07" }, "Stop")).toBe(true);
  });
});
