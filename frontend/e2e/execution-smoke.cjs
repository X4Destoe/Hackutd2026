const fs = require("node:fs/promises");
const BASE = process.env.STORM_URL || "http://127.0.0.1:5173";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
  });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
  });
  await context.route("https://**/*", (r) => r.abort());
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const api = async (path, body) => {
    const r = await context.request.fetch(BASE + "/api" + path, {
      method: body ? "POST" : "GET",
      data: body,
    });
    assert(r.ok(), path + " " + r.status());
    return r.json();
  };
  try {
    assert.equal(
      (await api("/messaging/status")).mode,
      "sim",
      "Run this test only with MESSAGING_MODE=sim",
    );
    await api("/demo/reset", { scenario_id: "harvey_houston" });
    await page.goto(BASE);
    await page
      .getByRole("main", { name: "Map workspace" })
      .getByRole("button", { name: /Bayou Plaza/ })
      .click();
    const card = page.getByRole("region", {
      name: "Building response actions",
    });
    await card.getByRole("button", { name: "Approve response plan" }).click();
    await card.getByText("Execution in progress", { exact: true }).waitFor();
    const orders = await api("/workorders?building_id=BLD-HOU-01");
    assert(orders.length > 0 && orders.every((o) => o.status === "sent"));
    const messages = await api("/messages");
    assert(
      messages.some((m) => m.kind === "task") &&
        messages.some((m) => m.kind === "tenant_notice"),
    );
    await page.getByRole("button", { name: "Texts", exact: true }).click();
    await page.getByLabel("Send as").selectOption("TECH-HOU-01");
    for (const order of orders) {
      await page.getByLabel("Message", { exact: true }).fill("DONE " + order.id);
      const start = Date.now();
      await page
        .getByRole("button", { name: "Send simulated message" })
        .click();
      await page.waitForFunction(async (id) => {
        const rows = await fetch("/api/workorders?building_id=BLD-HOU-01").then(
          (r) => r.json(),
        );
        return rows.find((o) => o.id === id)?.status === "done";
      }, order.id);
      assert(Date.now() - start < 2000, "completion exceeds 2 seconds");
    }
    await card.getByText("Response completed", { exact: true }).waitFor();
    assert(
      (await api("/workorders?building_id=BLD-HOU-01")).every(
        (o) => o.status === "done",
      ),
    );
    await fs.mkdir("/tmp/storm-map-acceptance", { recursive: true });
    await page.screenshot({
      path: "/tmp/storm-map-acceptance/response-completed.png",
    });
    assert.deepEqual(errors, []);
    console.log(
      "PASS real API/UI closed loop: map approval → workorders + simulated technician/tenant messages → simulator DONE replies → completed plan/card via SSE; no page errors",
    );
  } finally {
    await api("/demo/reset", { scenario_id: "harvey_houston" }).catch(() => {});
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
