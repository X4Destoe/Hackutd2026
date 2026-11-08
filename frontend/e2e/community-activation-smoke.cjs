// Resets an isolated simulator instance. Never use against real messaging.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1050 } });
  context.setDefaultTimeout(8000);
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
    await page.goto(BASE);
    await page.getByRole('navigation', { name: 'Portfolio tools' }).getByRole('button', { name: 'Help Sites', exact: true }).click();
    const activation = page.getByRole('article', { name: 'Help-site activation for Galleria Medical Offices' });
    await activation.getByRole('button', { name: 'Approve help-site activation', exact: true }).click();
    await activation.getByText(/Registered for routing/).waitFor();
    const sites = await api('/resources?city=Houston');
    const site = sites.find(site => site.building_id === 'BLD-HOU-04' && site.type === 'cbre_help_site');
    assert(site && site.capacity === 250 && site.status === 'open', 'Approval must register real routing capacity');
    const work = (await api('/workorders?building_id=BLD-HOU-04')).find(order => order.action_code === 'OFFER_HELP_SITE');
    assert(work && work.status === 'sent', 'Activation must dispatch a setup task');
    const messages = await api('/messages');
    assert(messages.some(message => message.work_order_id === work.id && message.kind === 'task' && message.channel === 'sim'));
    await activation.getByRole('button', { name: 'View setup tasks' }).click();
    await page.getByRole('region', { name: 'Portfolio content' }).getByRole('heading', { name: 'Work Orders', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Texts', exact: true }).click();
    await page.getByLabel('Send as').selectOption(work.party_id);
    await page.getByLabel('Message', { exact: true }).fill('DONE ' + work.id);
    await page.getByLabel('Photo URL (optional)').fill('https://example.com/setup-evidence.jpg');
    await page.getByRole('button', { name: 'Send simulated message', exact: true }).click();
    await page.getByText('Message submitted. Responses and updates appear below.', { exact: true }).waitFor();
    assert.equal((await api('/workorders')).find(order => order.id === work.id).status, 'done');
    assert((await api('/workorders')).find(order => order.id === work.id).photo_urls.includes('https://example.com/setup-evidence.jpg'));
    await page.getByRole('navigation', { name: 'Portfolio tools' }).getByRole('button', { name: 'Help Sites', exact: true }).click();
    await activation.getByText(`${work.id} · done`, { exact: true }).waitFor();
    assert.equal(await activation.getByRole('button', { name: 'Approve help-site activation', exact: true }).count(), 0, 'Do not offer duplicate approval');
    // A successful approval response alone must not be presented as confirmed registration.
    await api('/demo/reset', { scenario_id: 'harvey_houston' });
    await page.route('**/api/resources?city=Houston', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
    await page.reload();
    await page.getByRole('navigation', { name: 'Portfolio tools' }).getByRole('button', { name: 'Help Sites', exact: true }).click();
    await activation.getByRole('button', { name: 'Approve help-site activation', exact: true }).click();
    await activation.getByText('Registration unconfirmed', { exact: true }).waitFor();
    await activation.getByText(/no registered site is confirmed/).waitFor();
    assert.equal(await activation.getByText(/Registered for routing/).count(), 0);
    await page.unroute('**/api/resources?city=Houston');
    assert.deepEqual(errors, []);
    console.log('PASS CBRE help-site approval → registered community capacity → simulated setup text → technician DONE + photo → live completion; missing registration never shown as success');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
