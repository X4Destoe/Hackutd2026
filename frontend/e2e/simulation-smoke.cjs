// Full custom-scenario browser flow against an isolated simulator API.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1050 } });
  context.setDefaultTimeout(9000); await context.route('https://**/*', route => route.abort());
  const page = await context.newPage(); const errors = []; page.on('pageerror', error => errors.push(error.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), `${path}: HTTP ${response.status()}`); return response.json();
  };
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim'); resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' }); await page.goto(BASE);
    const open = async () => {
      await page.getByRole('button', { name: 'Build simulation', exact: true }).click();
      return page.getByRole('dialog', { name: 'Build a disaster simulation' });
    };
    const run = async dialog => {
      await dialog.getByRole('button', { name: 'Run custom simulation' }).click(); await dialog.waitFor({ state: 'hidden' });
      await page.getByText('Custom simulation · hypothetical effects', { exact: true }).waitFor();
      assert((await api('/demo/state')).scenario_id.startsWith('custom_'));
    };
    let dialog = await open(); await dialog.getByLabel('Simulation city').selectOption('dallas');
    await dialog.getByLabel('Simulation disaster').selectOption('winter');
    await dialog.getByRole('slider', { name: 'Minimum temperature' }).fill('-8');
    await dialog.getByRole('slider', { name: 'Ice accumulation' }).fill('1.1');
    await dialog.getByRole('slider', { name: 'Utility outage duration' }).fill('72'); await run(dialog);
    const custom = (await api('/demo/state')).scenario_id;
    const metadata = (await api('/scenarios')).find(scenario => scenario.id === custom);
    assert.equal(metadata.city, 'Dallas');
    const winterImpact = await api('/impact');
    assert(winterImpact.some(row => row.exposure.temp_f === -8 && row.exposure.ice_in === 1.1));
    await page.getByRole('button', { name: 'Fix-First', exact: true }).click();
    await page.getByRole('button', { name: 'Approve plan', exact: true }).first().click();
    await page.getByRole('button', { name: 'Work Orders', exact: true }).click();
    await page.getByRole('button', { name: 'Mark done', exact: true }).first().waitFor();
    const work = await api('/workorders'); assert(work.length && work.every(order => order.status === 'sent'));
    await page.getByRole('button', { name: 'Texts', exact: true }).click();
    for (const order of work) {
      await page.getByLabel('Send as').selectOption(order.party_id);
      await page.getByLabel('Message', { exact: true }).fill('DONE ' + order.id);
      await page.getByRole('button', { name: 'Send simulated message', exact: true }).click();
      await page.waitForFunction(id => fetch('/api/workorders').then(r => r.json()).then(rows => rows.find(row => row.id === id)?.status === 'done'), order.id);
    }
    assert((await api('/workorders')).every(order => order.status === 'done'));
    for (const depth of [2, 12]) {
      dialog = await open(); await dialog.getByLabel('Simulation city').selectOption('houston');
      await dialog.getByLabel('Simulation disaster').selectOption('flood');
      await dialog.getByRole('slider', { name: 'Peak water at exercise center' }).fill(String(depth)); await run(dialog);
      const damage = (await api('/impact')).reduce((sum, row) => sum + row.money.property_damage_cents, 0);
      if (depth === 2) page.lowDamage = damage; else assert(damage > page.lowDamage, 'Changing the water slider must change real modeled damage');
    }
    dialog = await open(); await dialog.getByRole('button', { name: 'Pick a random city' }).click();
    const picked = await dialog.getByLabel('Simulation city').inputValue(); assert(['houston', 'dallas', 'fort_myers'].includes(picked));
    await run(dialog); await page.screenshot({ path: '/tmp/storm-custom-simulation.png' });
    assert.deepEqual(errors, []);
    console.log('PASS custom Dallas winter → approval → simulator technician completion; Houston flood slider changes modeled damage; random supported city starts; honest custom labels and no page errors');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
