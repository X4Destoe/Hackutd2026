/* Live-service acceptance check. Run only against an isolated local demo: it resets state. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");
const BASE = process.env.STORM_URL || "http://127.0.0.1:5173";
const OUT = process.env.STORM_TEST_OUTPUT || "/tmp/storm-map-acceptance";
async function main() {
  await fs.mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  const api = async (route, method = "GET", body) => {
    const response = await context.request.fetch(`${BASE}/api${route}`, {
      method,
      data: body,
    });
    assert(response.ok(), `${method} ${route}: HTTP ${response.status()}`);
    return response.json();
  };
  try {
    assert.equal((await api("/messaging/status")).mode, "sim");
    await api("/demo/reset", "POST", { scenario_id: "harvey_houston" });
    await page.goto(BASE);
    const map = page.getByRole("main", { name: "Map workspace" });
    await map.waitFor();
    assert.equal(
      await map.getByText("Map module pending", { exact: true }).count(),
      0,
      "The live map is still a placeholder",
    );
    const marker = map.locator('[data-building-id="BLD-HOU-01"]');
    await marker.waitFor();
    await marker.click();
    await page
      .getByRole("region", { name: "Portfolio content" })
      .getByRole("heading", { name: "Bayou Plaza", exact: true })
      .waitFor();
    await page
      .getByRole("heading", { name: "Money waterfall", exact: true })
      .waitFor();
    await page.waitForFunction(
      () => document.querySelector(".storm-map")?.dataset.mapMoving === "false",
    );
    await page.screenshot({ path: path.join(OUT, "harvey-selected.png") });

    const before = await api("/portfolio/summary");
    const approvalStarted = Date.now();
    await page
      .getByRole("button", { name: "Approve plan", exact: true })
      .first()
      .click();
    await page.waitForFunction(
      () =>
        document.querySelector('[data-building-id="BLD-HOU-01"]')?.dataset
          .approved === "true",
    );
    assert(
      Date.now() - approvalStarted < 2000,
      "Approval marker did not refresh within 2 seconds",
    );
    const after = await api("/portfolio/summary");
    assert(
      after.avoided_cents > before.avoided_cents,
      "Approval did not increase avoided losses",
    );
    assert(
      after.net_exposure_cents < before.net_exposure_cents,
      "Approval did not reduce net exposure",
    );
    await page.screenshot({ path: path.join(OUT, "harvey-approved.png") });
    await page.getByRole("button", { name: "Map layers", exact: true }).click();
    const buildingToggle = page.getByRole("checkbox", {
      name: "Buildings by $ at risk",
      exact: true,
    });
    await buildingToggle.uncheck();
    await marker.waitFor({ state: "hidden" });
    await buildingToggle.check();
    await marker.waitFor({ state: "visible" });

    const impactStep = map.getByRole("button", {
      name: /(?:^|\s)0h(?:\s|$)|(?:hour|hours)\s*0\b/i,
    });
    const timelinePost = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/timeline" &&
        response.request().method() === "POST",
    );
    const overlayResponse = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/overlays" &&
        new URL(response.url()).searchParams.get("hour") === "0",
    );
    await impactStep.click();
    assert((await timelinePost).ok(), "Timeline mutation failed");
    assert.equal((await api("/demo/state")).step_hour, 0);
    await page.waitForFunction(() =>
      document
        .querySelector("#scenario-status")
        ?.textContent.includes("Impact:"),
    );
    assert((await overlayResponse).ok(), "Impact overlay request failed");
    await page.waitForTimeout(900); // Required 800ms visual rise animation, not a readiness surrogate.
    await page.screenshot({ path: path.join(OUT, "harvey-impact.png") });

    await page
      .getByRole("combobox", { name: "Disaster scenario" })
      .selectOption("uri_dallas");
    await page
      .getByRole("heading", { name: "Winter Storm Uri", exact: true })
      .waitFor();
    const dallas = map.getByRole("button", { name: /Lone Star Data Center/i });
    await dallas.waitFor();
    await dallas.click();
    await page
      .getByRole("region", { name: "Portfolio content" })
      .getByRole("heading", { name: "Lone Star Data Center", exact: true })
      .waitFor();
    assert.equal((await api("/demo/state")).scenario_id, "uri_dallas");

    // No external style/tile service is allowed for this context. Application code and APIs remain real.
    await context.route("https://**/*", (route) =>
      route.abort("blockedbyclient"),
    );
    await page.reload();
    await dallas.waitFor();
    await dallas.click();
    await page
      .getByRole("region", { name: "Portfolio content" })
      .getByRole("heading", { name: "Lone Star Data Center", exact: true })
      .waitFor();
    await page.screenshot({ path: path.join(OUT, "offline-basemap.png") });
    assert.deepEqual(
      pageErrors,
      [],
      `Browser exceptions: ${pageErrors.join("; ")}`,
    );
    console.log(
      "PASS live map markers/selection, approval ring + avoided losses, timeline mutation + SSE hero, scenario switching, offline marker interaction; screenshots: " +
        OUT,
    );
  } catch (error) {
    await page
      .screenshot({ path: path.join(OUT, "failure.png") })
      .catch(() => {});
    throw error;
  } finally {
    await api("/demo/reset", "POST", { scenario_id: "harvey_houston" }).catch(
      () => {},
    );
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
