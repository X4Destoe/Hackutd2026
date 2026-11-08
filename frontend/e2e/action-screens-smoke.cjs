// Run against an isolated demo instance: this resets its scenario state.
// STORM_URL=http://127.0.0.1:5173 node frontend/e2e/action-screens-smoke.cjs
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  context.setDefaultTimeout(8000);
  await context.route('https://**/*', route => route.abort());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, {
      method: body ? 'POST' : 'GET', data: body,
    });
    assert(response.ok(), `${path}: HTTP ${response.status()}`);
    return response.json();
  };
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim',
      'Use MESSAGING_MODE=sim; this test must never send real texts');
    resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' });
    await page.goto(BASE);
    await page.getByRole('button', { name: 'Fix-First', exact: true }).click();
    await page.getByRole('button', { name: 'Approve plan', exact: true }).first().click();
    await page.getByRole('button', { name: 'Work Orders', exact: true }).click();
    await page.getByRole('button', { name: 'Mark blocked', exact: true }).first().waitFor();
    const orders = await api('/workorders');
    assert(orders.length > 0, 'Approval must create actual work orders');
    const order = orders[0];
    const card = page.locator('.response-card').filter({ has: page.getByText(order.id, { exact: true }) });
    await card.getByRole('button', { name: 'Mark blocked', exact: true }).click();
    await card.getByText('Work order marked blocked.', { exact: true }).waitFor();
    assert.equal((await api('/workorders')).find(row => row.id === order.id).status, 'blocked');
    const filter = page.getByLabel('Filter work orders by status');
    await filter.selectOption('blocked');
    await card.getByRole('button', { name: 'Mark done', exact: true }).click();
    await page.getByText('No work orders match this status.', { exact: true }).waitFor();
    assert.equal((await api('/workorders')).find(row => row.id === order.id).status, 'done');
    await filter.selectOption('done');
    await card.getByText('done', { exact: true }).waitFor();
    assert.equal(await card.getByRole('button', { name: 'Mark done', exact: true }).count(), 0,
      'Completed orders must not expose another completion control');
    assert.deepEqual(errors, []);
    console.log('PASS Fix-First approval → real work orders → blocked/done controls → live filters; no page errors');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
