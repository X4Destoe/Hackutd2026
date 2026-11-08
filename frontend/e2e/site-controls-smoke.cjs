// Isolated demo only: resets state. Refuses real messaging before any mutation.
// STORM_URL=http://127.0.0.1:5173 node frontend/e2e/site-controls-smoke.cjs
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  context.setDefaultTimeout(7000);
  await context.route('https://**/*', route => route.abort());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), `${path}: ${response.status()}`);
    return response.json();
  };
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim', 'Use MESSAGING_MODE=sim');
    resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' });
    await page.goto(BASE);
    await page.waitForSelector('[data-map-ready="true"]');
    const tools = page.getByRole('navigation', { name: 'Portfolio tools' });
    const content = page.getByRole('region', { name: 'Portfolio content' });
    for (const [button, heading] of [['Fix-First', 'Fix-First'], ['Work Orders', 'Work Orders'], ['Help Sites', 'Help Sites'], ['Texts', 'Texts'], ['Reports', 'Reports']]) {
      await tools.getByRole('button', { name: button, exact: true }).click();
      await content.getByRole('heading', { name: heading, exact: true }).waitFor();
    }
    assert((await page.locator('.portfolio-totals').innerText()).includes('Estimated loss'));
    const reportsResponse = await context.request.get(BASE + '/api/reports');
    await content.getByRole('button', { name: 'Generate executive summary', exact: true }).click();
    if (reportsResponse.ok()) {
      await content.getByText('Report generated. Review the printable version below.', { exact: true }).waitFor();
      const reportUrl = await content.getByRole('link', { name: 'Open printable report' }).first().getAttribute('href');
      assert((await context.request.get(new URL(reportUrl, BASE).href)).ok(), 'Generated report must have a usable printable URL');
    } else {
      await content.getByRole('alert').filter({ hasText: 'Could not generate the report' }).waitFor();
      console.log('DEPENDENCY: report API unavailable; generate button exposes failure');
    }
    // Visible layer controls must change visible map output.
    const layers = page.getByRole('region', { name: 'Map layers' });
    await layers.getByRole('button', { name: 'Map layers', exact: true }).click();
    await layers.getByRole('button', { name: 'Clear', exact: true }).click();
    assert.equal(await page.locator('.map-activity button').count(), 0);
    await layers.getByRole('checkbox', { name: 'Help sites and residents' }).check();
    const activity = page.getByRole('complementary', { name: 'Operational map layers' });
    await activity.getByRole('button', { name: /Help sites/ }).click();
    await content.getByRole('heading', { name: 'Help Sites', exact: true }).waitFor();
    const resources = await context.request.get(BASE + '/api/resources?city=Houston');
    if (resources.ok()) {
      const sites = await resources.json();
      assert.equal(await page.locator('[data-activity-kind="help"]').count(), sites.length);
      if (sites.length) assert((await page.locator('[data-activity-kind="help"]').first().getAttribute('aria-label')).includes(sites[0].name), 'Help pins need descriptive accessible names');
      await tools.getByRole('button', { name: 'Texts', exact: true }).click();
      await page.getByLabel('Send as').selectOption('resident');
      await page.getByLabel('Resident phone').fill('+12145550123');
      await page.getByLabel('Message', { exact: true }).fill('Our apartment in Memorial flooded. 2 adults need shelter and a dry place.');
      await page.getByRole('button', { name: 'Send simulated message', exact: true }).click();
      await page.getByText('Message submitted. Responses and updates appear below.', { exact: true }).waitFor();
      const referrals = await api('/referrals');
      assert(referrals.length > 0 && referrals[0].status === 'routed', 'Resident request must create a routed referral');
      const destination = (await api('/resources?city=Houston')).find(site => site.id === referrals[0].resource_id);
      assert(destination && destination.used >= referrals[0].people, 'Routing must reserve real capacity');
      await tools.getByRole('button', { name: 'Help Sites', exact: true }).click();
      await content.getByText(referrals[0].party_id, { exact: true }).waitFor();
    } else {
      await activity.getByText('Unavailable · open details', { exact: true }).waitFor();
      console.log('DEPENDENCY: resource API unavailable; UI shows explicit unavailable state');
    }
    await layers.getByRole('button', { name: 'Select all', exact: true }).click();
    await page.getByRole('main', { name: 'Map workspace' }).getByRole('button', { name: /Bayou Plaza ·/ }).click();
    await page.getByRole('region', { name: 'Building response actions' }).getByRole('button', { name: 'Approve response plan' }).click();
    const orderPin = page.locator('[data-activity-kind="workorders"][data-activity-id="BLD-HOU-01"]');
    await orderPin.waitFor();
    await orderPin.click();
    await content.getByRole('heading', { name: 'Work Orders', exact: true }).waitFor();
    const textPin = page.locator('[data-activity-kind="messages"][data-activity-id="BLD-HOU-01"]');
    await textPin.click();
    await content.getByRole('heading', { name: 'Texts', exact: true }).waitFor();
    await layers.getByRole('checkbox', { name: 'Messages', exact: true }).uncheck();
    assert.equal(await page.locator('[data-activity-kind="messages"]').count(), 0);
    await layers.getByRole('checkbox', { name: 'Work orders', exact: true }).uncheck();
    assert.equal(await page.locator('[data-activity-kind="workorders"]').count(), 0);
    // Failed timeline clicks keep the real current step and expose retry feedback.
    const timeline = page.getByRole('navigation', { name: 'Disaster timeline' });
    const before = (await api('/demo/state')).step_hour;
    const impact = timeline.locator('button').filter({ has: page.locator('strong', { hasText: /^0h$/ }) });
    await page.route('**/api/timeline', route => route.request().method() === 'POST'
      ? route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }) : route.continue());
    await impact.click();
    await page.getByRole('alert').filter({ hasText: 'Could not confirm the timeline change' }).waitFor();
    assert.equal((await api('/demo/state')).step_hour, before);
    await page.unroute('**/api/timeline');
    await impact.click();
    await page.waitForFunction(() => document.querySelector('.storm-timeline button[aria-pressed="true"] strong')?.textContent === '0h');
    assert.equal((await api('/demo/state')).step_hour, 0);
    // Zoom controls must actually move marker positions; fit returns to the scenario.
    const buildingPin = page.locator('[data-building-id="BLD-HOU-01"]');
    await page.getByRole('button', { name: 'Fit the scenario', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('.storm-map')?.dataset.mapMoving === 'false');
    const fitted = await buildingPin.boundingBox();
    await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
    await page.waitForTimeout(600);
    const zoomed = await buildingPin.boundingBox();
    assert(Math.abs(fitted.x - zoomed.x) + Math.abs(fitted.y - zoomed.y) > 1, 'Zoom in must change the map');
    await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
    await page.getByRole('button', { name: 'Fit the scenario', exact: true }).click();
    // Selecting the same map record again must reopen a closed mobile drawer.
    await page.setViewportSize({ width: 800, height: 1000 });
    const panel = page.getByRole('complementary', { name: 'Portfolio panel' });
    await panel.getByRole('button', { name: 'Close portfolio panel', exact: true }).click();
    await page.getByRole('button', { name: 'Open map layers in portfolio panel' }).click();
    await panel.getByRole('button', { name: 'Close portfolio panel', exact: true }).waitFor();
    await panel.getByRole('button', { name: 'Close portfolio panel', exact: true }).click();
    await activity.getByRole('button', { name: /Help sites/ }).click();
    await panel.getByRole('heading', { name: 'Help Sites', exact: true }).waitFor();
    await panel.getByRole('button', { name: 'Close portfolio panel', exact: true }).click();
    await activity.getByRole('button', { name: /Help sites/ }).click();
    await panel.getByRole('heading', { name: 'Help Sites', exact: true }).waitFor();
    // The presenter can restart without an API console; cancellation and failure preserve the exercise.
    await page.setViewportSize({ width: 1600, height: 1100 });
    const beforeRestart = await api('/demo/state');
    const ordersBeforeRestart = (await api('/workorders')).length;
    assert(ordersBeforeRestart > 0, 'Approval must leave tasks for the restart test');
    let restartPosts = 0;
    await page.route('**/api/demo/reset', route => {
      restartPosts++;
      return route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    });
    await page.getByRole('button', { name: 'Restart current scenario', exact: true }).click();
    const restartDialog = page.getByRole('dialog', { name: 'Restart scenario?', exact: true });
    await restartDialog.getByRole('button', { name: 'Cancel', exact: true }).click();
    assert.equal(restartPosts, 0, 'Cancel must not issue a reset request');
    await page.getByRole('button', { name: 'Restart current scenario', exact: true }).click();
    await restartDialog.getByRole('button', { name: 'Restart scenario', exact: true }).click();
    await restartDialog.getByRole('alert').filter({ hasText: 'Could not confirm the restart' }).waitFor();
    assert.equal((await api('/demo/state')).step_hour, beforeRestart.step_hour);
    assert.equal((await api('/workorders')).length, ordersBeforeRestart);
    await page.unroute('**/api/demo/reset');
    await restartDialog.getByRole('button', { name: 'Restart scenario', exact: true }).click();
    await restartDialog.waitFor({ state: 'hidden' });
    assert.equal((await api('/demo/state')).scenario_id, beforeRestart.scenario_id);
    assert.equal((await api('/demo/state')).step_hour, -48);
    assert.equal((await api('/workorders')).length, 0);
    assert.equal((await api('/messages')).length, 0);
    assert.equal((await api('/referrals')).length, 0);
    assert.equal((await api('/reports')).length, 0);
    assert.equal((await api('/portfolio/summary')).actions_approved, 0);
    await content.getByRole('heading', { name: 'Portfolio overview', exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS navigation, layer output, operational record links, timeline failure/retry, repeated mobile panel opening, restart cancellation/failure/recovery and cleared workspace; no page errors');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
