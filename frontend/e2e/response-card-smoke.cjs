// Isolated simulator only: verifies map visibility controls preserve approved work.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  context.setDefaultTimeout(8000); await context.route('https://**/*', route => route.abort());
  const page = await context.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), `${path}: ${response.status()}`); return response.json();
  };
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim'); resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' }); await page.goto(BASE);
    const marker = page.locator('[data-building-id="BLD-HOU-01"]'); await marker.click();
    const card = page.getByRole('region', { name: 'Building response actions' });
    await card.getByRole('button', { name: 'Approve response plan', exact: true }).click();
    await card.locator('.map-workorder').first().waitFor();
    const orders = await api('/workorders'); assert(orders.length > 0);
    const first = card.locator('.map-workorder').first(); await first.locator('summary').click();
    const note = first.locator('textarea'); await note.fill('Draft progress note retained while minimized');
    const expanded = await card.boundingBox();
    await card.getByRole('button', { name: 'Minimize building response card' }).click();
    await card.getByRole('button', { name: 'Restore building response card' }).waitFor();
    assert((await card.boundingBox()).height < Math.min(100, expanded.height), 'Minimized card must free map space');
    assert.equal(await note.isVisible(), false);
    await card.getByRole('button', { name: 'Restore building response card' }).click();
    assert.equal(await note.inputValue(), 'Draft progress note retained while minimized');
    assert.equal(await note.isVisible(), true);
    await card.getByRole('button', { name: 'Close building response card' }).click();
    await card.waitFor({ state: 'hidden' });
    assert.equal((await api('/workorders')).length, orders.length);
    await marker.click(); await card.waitFor();
    await card.getByText('Execution in progress', { exact: true }).waitFor();
    await card.getByRole('button', { name: 'Close building response card' }).focus();
    await page.keyboard.press('Escape'); await card.waitFor({ state: 'hidden' });
    // The same marker can reopen the card; a mobile drawer can be closed independently.
    await page.setViewportSize({ width: 800, height: 1000 }); await marker.click();
    await page.getByRole('button', { name: 'Close portfolio panel', exact: true }).click();
    await card.getByRole('button', { name: 'Minimize building response card' }).click();
    await card.getByRole('button', { name: 'Restore building response card' }).click();
    await card.getByRole('button', { name: 'Close building response card' }).click();
    await card.waitFor({ state: 'hidden' });
    assert.equal((await api('/workorders')).length, orders.length);
    assert.deepEqual(errors, []);
    console.log('PASS response card minimizes/restores with draft intact, closes/Escape and reopens; approved work retained on desktop/mobile');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
