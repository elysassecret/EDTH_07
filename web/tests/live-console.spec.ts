import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { SceneMsg, Scorecard, Snapshot } from "../src/types";

const url = "/?evaluator&feed=ws://127.0.0.1:18870"; // truth view and evaluator controls
const operatorUrl = "/?feed=ws://127.0.0.1:18870"; // the default: the watch officer's screen
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

async function feed(page: Page, options: { acknowledge?: boolean } = {}) {
  let data = snapshot();
  let frozen = false;
  let scorecard: Scorecard | undefined;
  const clients = new Set<WebSocketRoute>();
  const commands: { cmd: string; id?: string; kind?: string; a?: number }[] =
    [];
  function deliver(socket: WebSocketRoute) {
    const truth = socket.url().endsWith("/truth");
    socket.send(
      JSON.stringify({
        ...data,
        view: truth ? "truth" : "shore",
        ...(truth
          ? {
              eval: {
                t: data.t,
                boats: [],
                contacts: [],
                links: [],
                seg_age: {},
                cable_overdue: null,
              },
              scorecard,
            }
          : {}),
      }),
    );
  }
  await page.routeWebSocket(/\/shore$|\/truth$/, (socket) => {
    clients.add(socket);
    socket.send(JSON.stringify(scene));
    deliver(socket);
    socket.onMessage((raw) => {
      const command = JSON.parse(String(raw));
      commands.push(command);
      if (options.acknowledge !== false)
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
    clients.forEach(deliver);
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
    scorecard: (value: Scorecard | undefined) => {
      scorecard = value;
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
    await page.goto(operatorUrl);
    await expect(page.getByLabel("TRUTH", { exact: true })).toHaveCount(0);
    const map = await page
      .getByRole("region", { name: "Operational chart", exact: true })
      .boundingBox();
    expect(map?.width).toBeGreaterThan(600);
    expect(map?.height).toBeGreaterThan(200);
    // no panel buttons in the top bar: the icon sidebars stay on their edges and open the drawers
    await expect(page.getByRole("button", { name: /^Attention ·/ })).toHaveCount(0);
    await expect(page.getByRole("navigation", { name: "Fleet sidebar" })).toBeVisible();
    await page.getByRole("button", { name: "Expand attention panel" }).click();
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

test("panels resize between limits, close when pushed past the minimum and come back", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto(operatorUrl);
    const chart = page.getByRole("region", { name: "Operational chart", exact: true });
    const fleetEdge = page.getByRole("separator", { name: "Resize fleet panel" });
    await expect(fleetEdge).toHaveAttribute("aria-valuenow", "280");
    const drag = async (dx: number, dy = 0) => {
      const box = (await fleetEdge.boundingBox())!;
      const x = box.x + box.width / 2;
      const y = box.y + box.height / 2;
      await page.mouse.move(x, y);
      await page.mouse.down();
      await page.mouse.move(x + dx / 2, y + dy, { steps: 4 });
      await page.mouse.move(x + dx, y + dy, { steps: 4 });
      await page.mouse.up();
    };
    const before = (await chart.boundingBox())!.width;
    await drag(1000); // far past the maximum
    await expect(fleetEdge).toHaveAttribute("aria-valuenow", "520");
    expect((await chart.boundingBox())!.width).toBeLessThan(before);
    await drag(-600); // pushed past the minimum: collapses to the icon sidebar, the chart takes the space
    await expect(fleetEdge).toHaveCount(0);
    await expect(page.getByRole("complementary", { name: "Fleet overview" })).toHaveCount(0);
    expect((await chart.boundingBox())!.width).toBeGreaterThan(before);
    // the collapsed panel stays as a narrow sidebar on the same (left) edge, one dot per boat
    const fleetRail = page.getByRole("navigation", { name: "Fleet sidebar" });
    const railBox = (await fleetRail.boundingBox())!;
    expect(railBox.x).toBeLessThan(10);
    expect(railBox.width).toBeLessThanOrEqual(56);
    await expect(fleetRail.getByRole("button", { name: /^USV \d\d/ }).first()).toBeVisible();
    await fleetRail.getByRole("button", { name: "Expand fleet panel" }).click();
    await expect(fleetRail).toHaveCount(0);
    await expect(page.getByRole("separator", { name: "Resize fleet panel" })).toHaveAttribute("aria-valuenow", "520");
    // keyboard: arrows resize, Enter hides; the layout is remembered across a reload
    const attEdge = page.getByRole("separator", { name: "Resize attention panel" });
    await attEdge.focus();
    await page.keyboard.press("Home");
    await expect(attEdge).toHaveAttribute("aria-valuenow", "320");
    await page.getByRole("button", { name: "Collapse attention panel" }).click();
    const attRail = page.getByRole("navigation", { name: "Attention sidebar" });
    const attBox = (await attRail.boundingBox())!;
    expect(attBox.x + attBox.width).toBeGreaterThan(1600 - 10); // on the right edge
    await expect(attRail.getByRole("button", { name: /^Decisions waiting: \d+/ })).toBeVisible();
    await attRail.getByRole("button", { name: "Expand attention panel" }).click();
    await page.getByRole("button", { name: "Collapse event timeline" }).click();
    await expect(page.getByRole("region", { name: "Event timeline" })).toHaveCount(0);
    await page.reload();
    await expect(page.getByRole("separator", { name: "Resize attention panel" })).toHaveAttribute("aria-valuenow", "320");
    await expect(page.getByRole("region", { name: "Event timeline" })).toHaveCount(0);
    const timelineTab = page.getByRole("button", { name: /^Expand event timeline/ });
    const tabBox = (await timelineTab.boundingBox())!;
    expect(tabBox.y + tabBox.height).toBeGreaterThan(1000 - 10); // along the bottom edge
    await timelineTab.click();
    await expect(page.getByRole("region", { name: "Event timeline" })).toBeVisible();
  } finally {
    wire.stop();
  }
});

test("drawers leave the way they came in, and Help opens the guides", async ({ page }) => {
  const wire = await feed(page);
  try {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto(operatorUrl);
    await expect(page.getByText("FEED LIVE")).toBeVisible();
    await page.waitForTimeout(2000); // let the chart finish its first load before timing frames
    const xs = async (act: () => Promise<void>) => {
      await page.evaluate(() => {
        const w = window as unknown as { __x: number[] };
        w.__x = [];
        const t0 = performance.now();
        const tick = () => {
          const el = document.querySelector('[data-slot="sheet-content"]');
          if (el) w.__x.push(el.getBoundingClientRect().x);
          if (performance.now() - t0 < 1500) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
      await act();
      await page.waitForTimeout(1600);
      return page.evaluate(() => (window as unknown as { __x: number[] }).__x);
    };
    // fleet: in from the left, out to the left (it used to slide out to the right)
    const open = await xs(() => page.getByRole("button", { name: "Expand fleet panel" }).click());
    expect(open.at(-1)! - open[0]).toBeGreaterThan(50);
    await expect(page.getByRole("dialog", { name: "Fleet overview" })).toBeVisible();
    const close = await xs(() => page.keyboard.press("Escape"));
    expect(close.at(-1)! - close[0]).toBeLessThan(-50);
    // Help used to hang the tab on a guide line it could not parse
    await page.getByRole("button", { name: "Help" }).click();
    const guide = page.getByRole("dialog", { name: "Watch guide" });
    await expect(guide).toBeVisible();
    await guide.locator("summary", { hasText: "What the simulator models" }).click();
    await expect(guide.getByRole("cell", { name: "Battery swap", exact: true })).toBeVisible();
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
    // Measure contrast only after fade/zoom animations end, not on a half-faded frame.
    const settled = () =>
      page.waitForFunction(() =>
        document.getAnimations().every((a) => a.playState !== "running"),
      );
    await settled();
    let result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
    await page.getByRole("button", { name: /Review & approve/ }).click();
    await page.getByRole("dialog").waitFor();
    await settled();
    result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  } finally {
    wire.stop();
  }
});

test("restoration sends boat_restore for the selected boat and requires a fresh feed", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    await page.goto(url);
    await page.getByRole("button", { name: "Exercise controls" }).click();
    const dialog = page.getByRole("dialog", { name: "Exercise controls" });
    await dialog.getByRole("combobox", { name: "Exercise boat" }).click();
    await page.getByRole("option", { name: "USV 03", exact: true }).click();
    const restore = dialog.getByRole("button", {
      name: "Switch back on",
      exact: true,
    });
    await expect(restore).toBeEnabled();
    await restore.click();
    await expect
      .poll(() => wire.commands)
      .toEqual([{ cmd: "inject", kind: "boat_restore", a: 3 }]);
    wire.freeze();
    await expect(restore).toBeDisabled({ timeout: 15000 });
    wire.resume();
    await expect(restore).toBeEnabled();
    expect(wire.commands).toHaveLength(1);
  } finally {
    wire.stop();
  }
});

test("scorecard stays evaluator-only and preserves provenance, preliminary and missing states", async ({
  page,
}) => {
  const wire = await feed(page);
  try {
    wire.scorecard({
      source: "test-fixture/evaluator",
      seeds: [1, 2],
      preliminary: true,
      rows: [
        {
          mode: "elysa",
          metric: "fixture metric",
          median: 1,
          min: 0,
          max: 2,
          unit: "km",
        },
      ],
    });
    await page.goto(operatorUrl);
    await expect(page.getByText(/test-fixture\/evaluator/)).toHaveCount(0);
    await page.getByRole("button", { name: "View settings" }).click();
    await expect(page.getByRole("switch", { name: /Evaluator comparison/ })).toHaveCount(0);
    await page.goto(url); // ?evaluator turns the comparison on at load
    await expect(page.getByText("PRELIMINARY", { exact: true })).toBeVisible();
    await expect(
      page.getByText("test-fixture/evaluator · seeds 1, 2", { exact: true }),
    ).toBeVisible();
    wire.scorecard(undefined);
    await expect(
      page.getByText("Waiting for eval/ scorecard. No results are invented.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByText("PRELIMINARY", { exact: true })).toHaveCount(0);
  } finally {
    wire.stop();
  }
});

test("an unconfirmed answer blocks its own retry but releases unrelated decisions", async ({
  page,
}) => {
  const wire = await feed(page, { acknowledge: false });
  try {
    const first = snapshot().decisions[0];
    wire.update({
      decisions: [
        first,
        {
          ...first,
          id: "close:contact:C-08",
          task: "contact:C-08",
          text: "A separate delivered proposal",
          t: 951,
        },
      ],
    });
    await page.goto(url);
    const original = page.getByRole("article", {
      name: /Decision close:contact:C-07\./,
    });
    await original.getByRole("button", { name: /Review & approve/ }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Authorize & send" })
      .click();
    await expect(
      original.getByText("DELIVERY UNCONFIRMED", { exact: true }),
    ).toBeVisible({ timeout: 20000 });
    await expect(
      original.getByRole("button", { name: /Review & approve/ }),
    ).toBeDisabled();
    const other = page.getByRole("article", {
      name: /Decision close:contact:C-08\./,
    });
    await other.getByRole("button", { name: /Review & approve/ }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Authorize & send" })
      .click();
    await expect(
      page.getByRole("button", { name: "Undo queued answer" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Undo queued answer" }).click();
    expect(wire.commands.filter((c) => c.cmd === "approve")).toHaveLength(1);
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
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Pause simulation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Run simulation" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
