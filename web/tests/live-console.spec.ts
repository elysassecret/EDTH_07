import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { SceneMsg, Snapshot } from "../src/types";

const url = "/?feed=ws://127.0.0.1:18870";
const scene: SceneMsg = {
  type: "scene",
  schema_version: 1,
  source: "sim",
  t0_utc: "2026-11-03T10:15:00Z",
  shore: [11.1303, 55.3316],
  stations: { relay: [10.975, 55.405] },
  stale_after_s: 60,
  horizon_s: 14400,
  revisit_target_s: 12000,
  segments: {
    "seg:H:2": [
      [10.87, 55.45],
      [10.95, 55.47],
    ],
    "seg:M:0": [
      [10.96, 55.32],
      [10.9, 55.3],
    ],
  },
};
function snapshot(): Snapshot {
  return {
    type: "snapshot",
    schema_version: 1,
    source: "sim",
    seed: 1,
    view: "shore",
    t: 1000,
    speed: 1,
    warp_mode: "manual",
    t0_utc: scene.t0_utc,
    boats: [1, 2, 3, 4, 5].map((id) => ({
      id,
      mode: "PATROL",
      x: 0,
      y: 0,
      lon: 10.96 + id * 0.01,
      lat: 55.36 + id * 0.015,
      batt: 800,
      endurance_s: 20000,
      must_return_by: 12000,
      link: "direct",
      via: 0,
      last_heard: 1000,
      roles: ["seg:H:2"],
      tour: ["seg:H:2"],
      hdg: 45,
      sog: 2300,
    })),
    tasks: { "contact:C-07": { v: 2, owner: 3, deputy: 2, state: 1 } },
    contacts: [
      {
        id: "contact:C-07",
        track: "C-07",
        x: 0,
        y: 0,
        lon: 10.9,
        lat: 55.45,
        cog: 0,
        sog: 206,
        ais: false,
        first_seen: 900,
        last_seen: 999,
        seen_by: [2],
        watcher: 3,
        state: 1,
        source: "camera",
        flags: { dwell: true },
      },
    ],
    decisions: [
      {
        id: "close:contact:C-07",
        task: "contact:C-07",
        text: "LIVE REPORT: USV 03 close to 500 m for a look",
        dec: "close",
        state: "pending",
        t: 950,
        tier: "held",
        boat: 3,
        actions: ["approve", "decline"],
        route: [
          [10.99, 55.405],
          [10.9, 55.45],
        ],
      },
    ],
    alerts: [],
    events: [
      {
        t: 990,
        kind: "contact_reported",
        text: "Live fixture event from the feed",
      },
    ],
    links: [
      { a: 0, b: 4, state: "up" },
      { a: 1, b: 4, state: "cut" },
    ],
    seg_age: { "seg:H:2": 30 },
  };
}

async function feed(page: Page) {
  let data = snapshot();
  let frozen = false;
  const clients = new Set<WebSocketRoute>();
  const commands: { cmd: string; id?: string }[] = [];
  await page.routeWebSocket(/\/shore$|\/truth$/, (socket) => {
    clients.add(socket);
    socket.send(JSON.stringify(scene));
    const view = socket.url().endsWith("/truth") ? "truth" : "shore";
    socket.send(JSON.stringify({ ...data, view }));
    socket.onMessage((raw) => {
      const command = JSON.parse(String(raw));
      commands.push(command);
      socket.send(
        JSON.stringify({
          type: "ack",
          cmd: command.cmd,
          id: command.id ?? null,
          ok: true,
        }),
      );
    });
    socket.onClose(() => clients.delete(socket));
  });
  const timer = setInterval(() => {
    if (frozen) return;
    data = {
      ...data,
      t: data.t + 0.1,
      boats: data.boats.map((b) => ({ ...b, last_heard: data.t })),
    };
    clients.forEach((socket) =>
      socket.send(
        JSON.stringify({
          ...data,
          view: socket.url().endsWith("/truth") ? "truth" : "shore",
        }),
      ),
    );
  }, 100);
  return {
    commands,
    freeze: () => {
      frozen = true;
    },
    resume: () => {
      frozen = false;
    },
    update: (patch: Partial<Snapshot>) => {
      data = { ...data, ...patch };
    },
    stop: () => clearInterval(timer),
  };
}

test("template shell uses protocol data, not prototype scenarios, and keeps the map", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    const external: string[] = [];
    await page.route("**/*", (route) => {
      if (
        route.request().url().startsWith("http://127.0.0.1:18870/") ||
        route.request().url().startsWith("data:")
      )
        return route.continue();
      external.push(route.request().url());
      return route.abort();
    });
    await page.goto(url);
    await expect(
      page.getByRole("heading", { name: "Fleet overview", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("LIVE REPORT: USV 03 close to 500 m for a look", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".maplibregl-canvas")).toBeVisible();
    await expect(page.getByText("D-031", { exact: true })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Scenarios", exact: true }),
    ).toHaveCount(0);
    await page
      .getByTestId("fleet-4")
      .getByRole("button", { name: "USV 04" })
      .click();
    await expect(page.getByText("USV 01 — USV 04:")).toBeVisible();
    await expect(
      page.getByText("Direct to shore", { exact: true }).last(),
    ).toBeVisible();
    expect(external).toEqual([]);
    await page.screenshot({
      path: "test-results/live-desktop.png",
      fullPage: true,
      animations: "disabled",
    });
  } finally {
    wire.stop();
  }
});

test("review, undo and server acceptance do not manufacture asset delivery", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.goto(url);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("heading", { name: "Approve proposed action" }),
    ).toBeVisible();
    expect(wire.commands).toHaveLength(0);
    await dialog.getByRole("button", { name: "Authorize & send" }).click();
    await page.getByRole("button", { name: "Undo queued answer" }).click();
    await page.waitForTimeout(5200);
    expect(wire.commands.filter((c) => c.cmd === "approve")).toHaveLength(0);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Authorize & send" })
      .click();
    await expect
      .poll(() => wire.commands.filter((c) => c.cmd === "approve").length, {
        timeout: 8000,
      })
      .toBe(1);
    await expect(
      page.getByText("Accepted by server · await boat report", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("ACCEPTED BY ASSET", { exact: true }),
    ).toHaveCount(0);
  } finally {
    wire.stop();
  }
});

test("feed loss freezes the picture and cancels unsent answers on an open socket", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.goto(url);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Authorize & send" })
      .click();
    wire.freeze();
    await expect(page.getByText("FEED LOST", { exact: true })).toBeVisible({
      timeout: 15000,
    });
    await expect(
      page.getByRole("button", { name: "Pause simulation" }),
    ).toBeDisabled();
    await page.waitForTimeout(5500);
    expect(wire.commands.filter((c) => c.cmd === "approve")).toHaveLength(0);
    wire.resume();
    await expect(
      page.getByRole("button", { name: "Pause simulation" }),
    ).toBeEnabled();
    await expect(page.getByText("FEED LOST", { exact: true })).toHaveCount(0);
  } finally {
    wire.stop();
  }
});

test("expired reviews cannot submit and truth view is read-only", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.goto(url);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    wire.update({
      decisions: [{ ...snapshot().decisions[0], state: "expired" }],
    });
    await expect(
      page.getByText("Decision changed or expired", { exact: true }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("dialog")
        .getByRole("button", { name: "Authorize & send" }),
    ).toBeDisabled();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Back to review" })
      .click();
    wire.update({ decisions: snapshot().decisions });
    await page.getByLabel("TRUTH", { exact: true }).click();
    await expect(
      page.getByText("TRUTH VIEW — evaluator only", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Review & approve/ }),
    ).toBeDisabled();
    expect(wire.commands).toHaveLength(0);
  } finally {
    wire.stop();
  }
});

test("laptop sheets preserve chart space and operator mode never exposes truth", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto(`${url}&operator`);
    await expect(page.getByLabel("TRUTH", { exact: true })).toHaveCount(0);
    const map = await page
      .getByRole("region", { name: "Operational chart", exact: true })
      .boundingBox();
    expect(map?.width).toBeGreaterThan(600);
    expect(map?.height).toBeGreaterThan(200);
    await page
      .getByRole("button", { name: "Attention · 1", exact: true })
      .click();
    await expect(
      page.getByRole("dialog", { name: "Operator attention" }),
    ).toBeVisible();
    await page.screenshot({
      path: "test-results/live-laptop.png",
      fullPage: true,
      animations: "disabled",
    });
    await page
      .getByRole("dialog", { name: "Operator attention" })
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await page.getByRole("button", { name: "View settings" }).click();
    await expect(
      page.getByRole("switch", { name: /Evaluator comparison/ }),
    ).toHaveCount(0);
  } finally {
    wire.stop();
  }
});

test("primary screen and focused review pass automated accessibility checks", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.goto(url);
    await page.getByRole("button", { name: /Review & approve/ }).waitFor();
    let result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  } finally {
    wire.stop();
  }
});

test("real simulator handshake and pause work without the template fixture", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url);
  await expect(page.getByText("FEED LIVE", { exact: true })).toBeVisible();
  await expect(page.getByTestId("fleet-4")).toBeVisible();
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Resume simulation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Resume simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Pause simulation" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
