// Real API setup + an explicitly simulated provider-failure GET fixture; no real texts.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1050 } });
  context.setDefaultTimeout(7000);
  await context.route('https://**/*', route => route.abort());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), `${path}: HTTP ${response.status()}`);
    return response.json();
  };
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim', 'Use MESSAGING_MODE=sim');
    resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' });
    const plan = (await api('/fix-first')).find(plan => plan.building_id === 'BLD-HOU-01');
    await api(`/plans/${plan.plan_id}/approve`, { by: 'MGR-01' });
    const messages = await api('/messages');
    const task = messages.find(message => message.kind === 'task');
    assert(task?.work_order_id, 'Real approval must create a linked task message');
    const failed = { ...task, id: 'MSG-TEST-FAILURE', status: 'failed', error: 'Simulated provider rejection for browser acceptance.' };
    await page.route('**/api/messages', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([...messages, failed]) }));
    await page.goto(BASE);
    await page.getByRole('button', { name: 'Texts', exact: true }).click();
    const card = page.getByRole('listitem', { name: 'Message MSG-TEST-FAILURE' });
    await card.getByText(`Failed to send to ${task.party_id}`, { exact: true }).waitFor();
    assert.equal(await card.getByText(`Sent to ${task.party_id}`, { exact: true }).count(), 0);
    await page.getByRole('checkbox', { name: 'Show messages needing follow-up' }).check();
    assert.equal(await page.locator('.message-outbound').count(), 1);
    await page.getByLabel('Filter messages by conversation').selectOption(task.party_id);
    await card.getByRole('button', { name: 'Review work order' }).click();
    await page.getByRole('region', { name: 'Portfolio content' }).getByRole('heading', { name: 'Work Orders', exact: true }).waitFor();
    assert.equal((await api('/messages')).length, messages.length, 'Review/filter must not send another message');
    assert.deepEqual(errors, []);
    console.log('PASS failed-message wording, follow-up and conversation filters, linked work-order navigation; no resend or page errors');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
