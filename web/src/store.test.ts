import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Snapshot } from "./types";

class Socket {
  static OPEN = 1;
  static instances: Socket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  sent: string[] = [];
  constructor(public url: string) {
    Socket.instances.push(this);
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  frame(value: unknown) {
    this.onmessage?.({ data: JSON.stringify(value) });
  }
  send(value: string) {
    this.sent.push(value);
  }
}
function frame(t = 100, seed = 1): Snapshot {
  return {
    seed,
    view: "shore",
    t,
    speed: 240,
    boats: [],
    contacts: [],
    links: [],
    alerts: [],
    events: [],
    seg_age: {},
    tasks: { "contact:C-07": { v: 2, owner: 3, deputy: 2, state: 1 } },
    decisions: [
      {
        id: "close:contact:C-07",
        task: "contact:C-07",
        text: "Close for a look",
        dec: "close",
        state: "pending",
        t: 50,
        tier: "held",
        boat: 3,
        actions: ["approve", "decline"],
      },
    ],
  };
}
async function setup(search = "") {
  vi.stubGlobal("window", {
    location: { search, hostname: "localhost" },
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
  });
  const store = await import("./store");
  store.connect();
  const socket = Socket.instances.at(-1)!;
  socket.open();
  socket.frame(frame());
  return { ...store, socket };
}
beforeEach(() => {
  vi.resetModules();
  vi.useFakeTimers({
    toFake: [
      "setTimeout",
      "clearTimeout",
      "setInterval",
      "clearInterval",
      "Date",
      "performance",
    ],
  });
  Socket.instances = [];
  vi.stubGlobal("WebSocket", Socket);
});
afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("operational transport retained by the template integration", () => {
  it("blocks commands on a stale but still-open socket and cancels the undo queue", async () => {
    const { useStore, socket } = await setup();
    expect(
      useStore
        .getState()
        .holdAnswer({ cmd: "approve", id: "close:contact:C-07" }, "approve"),
    ).toBe(true);
    vi.advanceTimersByTime(6000);
    expect(useStore.getState().conn).toBe("lost");
    expect(useStore.getState().held).toBeNull();
    expect(useStore.getState().lastAck).toBeNull();
    expect(socket.sent).toEqual([]);
    expect(useStore.getState().send({ cmd: "pause" })).toBe(false);
  });
  it("rechecks report age at dispatch even before the watchdog runs", async () => {
    const { useStore, socket } = await setup();
    const clock = vi
      .spyOn(performance, "now")
      .mockReturnValue(useStore.getState().lastMsgAt + 2100);
    try {
      expect(useStore.getState().send({ cmd: "pause" })).toBe(false);
      expect(useStore.getState().conn).toBe("lost");
      expect(socket.sent).toEqual([]);
    } finally {
      clock.mockRestore();
    }
  });
  it("releases the transport slot after loss without fabricating an acknowledgment", async () => {
    const { useStore, socket } = await setup();
    useStore.setState({ answering: "close:contact:C-07" });
    socket.close();
    expect(useStore.getState().conn).toBe("lost");
    expect(useStore.getState().answering).toBeNull();
    expect(useStore.getState().lastAck).toBeNull();
    expect(socket.sent).toEqual([]);
  });
  it("does not transmit a queued decision that expires during its undo window", async () => {
    const { useStore, socket } = await setup();
    useStore
      .getState()
      .holdAnswer({ cmd: "approve", id: "close:contact:C-07" }, "approve");
    for (let i = 1; i <= 5; i++) {
      vi.advanceTimersByTime(900);
      const value = frame(100 + i);
      value.decisions[0].state = "expired";
      socket.frame(value);
    }
    vi.advanceTimersByTime(600);
    expect(socket.sent).toEqual([]);
    expect(useStore.getState().commandError).toContain("task changed");
  });
  it("sends a valid unchanged answer once, only after the undo window", async () => {
    const { useStore, socket } = await setup();
    useStore
      .getState()
      .holdAnswer({ cmd: "approve", id: "close:contact:C-07" }, "approve");
    expect(
      useStore
        .getState()
        .holdAnswer({ cmd: "decline", id: "close:contact:C-07" }, "duplicate"),
    ).toBe(false);
    for (let i = 1; i <= 5; i++) {
      vi.advanceTimersByTime(900);
      socket.frame(frame(100 + i));
    }
    expect(socket.sent).toHaveLength(0);
    vi.advanceTimersByTime(600);
    expect(socket.sent.map((raw) => JSON.parse(raw))).toEqual([
      { cmd: "approve", id: "close:contact:C-07" },
    ]);
    expect(useStore.getState().answering).toBe("close:contact:C-07");
  });
  it("cancels queued answers on seed reset without inventing an acknowledgment", async () => {
    const { useStore, socket } = await setup();
    useStore
      .getState()
      .holdAnswer({ cmd: "approve", id: "close:contact:C-07" }, "approve");
    socket.frame(frame(0, 2));
    expect(useStore.getState().held).toBeNull();
    expect(useStore.getState().lastAck).toBeNull();
    expect(useStore.getState().commandError).toContain("simulation reset");
    expect(socket.sent).toEqual([]);
  });
  it("discards frames from the previous channel and keeps truth read-only", async () => {
    const { useStore, socket } = await setup("?evaluator");
    useStore.getState().setChannel("truth");
    const truth = Socket.instances.at(-1)!;
    truth.open();
    truth.frame({ ...frame(), view: "truth" });
    socket.frame(frame(900));
    expect(useStore.getState().snap?.view).toBe("truth");
    expect(useStore.getState().snap?.t).toBe(100);
    expect(
      useStore.getState().send({ cmd: "approve", id: "close:contact:C-07" }),
    ).toBe(false);
    expect(truth.sent).toEqual([]);
  });
  it.each(["", "?operator"])("cannot expose the truth channel on the default operator screen (%s)", async (q) => {
    const { useStore } = await setup(q);
    expect(useStore.getState().evalOn).toBe(false);
    useStore.getState().setChannel("truth");
    expect(useStore.getState().channel).toBe("shore");
    useStore.getState().toggleEval();
    expect(useStore.getState().evalOn).toBe(false);
  });
  it("?evaluator starts with the comparison on and its /truth socket open (#88)", async () => {
    const { useStore } = await setup("?evaluator");
    expect(useStore.getState().evalOn).toBe(true);
    expect(Socket.instances.some((x) => String(x.url).endsWith("/truth"))).toBe(true);
  });
});
