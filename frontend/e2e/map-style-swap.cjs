/* Real APIs + local basemap-style response. No mock hazard, finance or action data. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const { chromium } = require("playwright");
const BASE = process.env.STORM_URL || "http://127.0.0.1:5173";
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
  });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  await context.route(
    "https://tiles.openfreemap.org/styles/liberty",
    async (route) => {
      await gate;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          version: 8,
          sources: {},
          layers: [
            {
              id: "local-test-basemap",
              type: "background",
              paint: { "background-color": "#ecf1e5" },
            },
          ],
        }),
      });
    },
  );
  const api = async (path, body) => {
    const r = await context.request.fetch(BASE + "/api" + path, {
      method: body ? "POST" : "GET",
      data: body,
    });
    assert(r.ok(), path + " HTTP " + r.status());
    return r.json();
  };
  try {
    await api("/demo/reset", { scenario_id: "harvey_houston" });
    await api("/timeline", { hour: 0 });
    await page.goto(BASE);
    await page.waitForFunction(
      () =>
        Number(document.querySelector(".storm-map")?.dataset.waterRendered) > 0,
    );
    const first = await page
      .locator(".storm-map")
      .getAttribute("data-style-generation");
    release();
    await page.waitForFunction((first) => {
      const root = document.querySelector(".storm-map");
      return (
        root?.dataset.basemap === "remote" &&
        Number(root.dataset.styleGeneration) > Number(first) &&
        Number(root.dataset.waterRendered) > 0 &&
        Number(root.dataset.powerRendered) > 0
      );
    }, first);
    await page
      .getByRole("main", { name: "Map workspace" })
      .getByRole("button", { name: /Bayou Plaza/ })
      .click();
    const card = page.getByRole("region", {
      name: "Building response actions",
    });
    await card.waitFor();
    await card
      .getByRole("heading", { name: "Bayou Plaza", exact: true })
      .waitFor();
    await fs.mkdir("/tmp/storm-map-acceptance", { recursive: true });
    await page.screenshot({
      path: "/tmp/storm-map-acceptance/style-swap-impact.png",
    });
    // Return to forecast for an actionable pre-storm plan, then approve through the map card itself.
    await api("/demo/reset", { scenario_id: "harvey_houston" });
    await page
      .getByRole("main", { name: "Map workspace" })
      .getByRole("button", { name: /Bayou Plaza/ })
      .click();
    await card.getByRole("button", { name: "Approve response plan" }).waitFor();
    const before = await api("/portfolio/summary");
    await card.getByRole("button", { name: "Approve response plan" }).click();
    await page.waitForFunction(
      () =>
        document.querySelector('[data-building-id="BLD-HOU-01"]')?.dataset
          .approved === "true",
    );
    await card.getByText("Plan approved", { exact: true }).waitFor();
    await card.getByText(/task delivery is not confirmed/).waitFor();
    const after = await api("/portfolio/summary");
    assert(after.avoided_cents > before.avoided_cents);
    await page.screenshot({
      path: "/tmp/storm-map-acceptance/action-card-approved.png",
    });
    const sizes = await page
      .locator(".storm-building-square")
      .evaluateAll((nodes) =>
        nodes.map((node) => Math.round(node.getBoundingClientRect().width)),
      );
    assert(
      new Set(sizes).size > 1,
      "Building sizes must differ by replacement value",
    );
    const clipped = await page.locator(".storm-building-label").evaluateAll(
      (labels) =>
        labels.filter((label) => {
          const parent = label.closest(".maplibregl-map");
          const point = label.parentElement.getBoundingClientRect();
          const bounds = parent.getBoundingClientRect();
          const r = label.getBoundingClientRect();
          return (
            point.left > bounds.left + 40 &&
            point.left < bounds.right - 40 &&
            (r.left < bounds.left || r.right > bounds.right)
          );
        }).length,
    );
    assert.equal(clipped, 0, "Visible labels clip at map edge");
    assert.deepEqual(errors, []);
    console.log(
      "PASS remote-style swap retains rendered water/power; map-card approval updates model and reports unconfirmed dispatch honestly; distinct marker sizes; visible labels stay in bounds",
    );
  } finally {
    release();
    await api("/demo/reset", { scenario_id: "harvey_houston" }).catch(() => {});
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
