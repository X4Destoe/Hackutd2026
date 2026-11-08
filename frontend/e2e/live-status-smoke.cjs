// Browser fixtures for a live scenario until the runtime scenario integration is available.
const assert = require('node:assert/strict');
const http = require('node:http');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const connections = new Set();
  const events = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-cache' });
    res.write(': connected\n\n'); connections.add(res); req.on('close', () => connections.delete(res));
  });
  await new Promise(resolve => events.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  page.setDefaultTimeout(8000);
  await page.route('https://**/*', route => route.abort());
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const state = await (await page.request.get(BASE + '/api/demo/state')).json();
  const scenarios = await (await page.request.get(BASE + '/api/scenarios')).json();
  let status = { feeds: {}, refreshing: false, alert_count: 1, alerts_without_area: 0 };
  let fail = false;
  const update = () => connections.forEach(res => res.write('event: live.updated\ndata: {}\n\n'));
  await page.route('**/api/events', route => route.continue({ url: `http://127.0.0.1:${events.address().port}/events` }));
  await page.route('**/api/demo/state', route => route.fulfill({ json: { ...state, scenario_id: 'live_houston' } }));
  await page.route('**/api/scenarios', route => route.fulfill({ json: [...scenarios, { ...scenarios.find(s => s.city === 'Houston'), id: 'live_houston', name: 'Live screening' }] }));
  await page.route('**/api/live/status', route => route.fulfill(fail ? { status: 503, json: {} } : { json: status }));
  await page.route('**/api/overlays*', route => route.fulfill({ json: { type: 'FeatureCollection', features: [{ type: 'Feature',
    properties: { style: 'flood_water', hazard: 'flood', intensity: 2, event: 'Flood Warning', headline: 'Browser fixture warning', severity: 'Severe' },
    geometry: { type: 'Polygon', coordinates: [[[-97,28],[-94,28],[-94,32],[-97,32],[-97,28]]] } }] } }));
  try {
    await page.goto(BASE);
    const quality = page.getByRole('region', { name: 'Live data quality' });
    await quality.getByText('Some inputs are stale or unknown', { exact: true }).waitFor();
    await quality.getByText('Data sources and limits', { exact: true }).click();
    assert.equal(await quality.getByText('Unknown · never fetched', { exact: true }).count(), 3);
    const now = new Date().toISOString();
    status.feeds = Object.fromEntries(['alerts', 'forecast:Houston', 'gauges:Houston'].map(key => [key, { as_of: now, stale: false, error: null }]));
    await page.waitForTimeout(300); assert(connections.size === 1, 'Use one active shared EventSource'); update();
    await quality.getByText('Source fetches are current', { exact: true }).waitFor();
    await quality.getByText('Power status unverified · screening only', { exact: true }).waitFor();
    fail = true; update();
    await quality.getByRole('button', { name: 'Retry live status' }).waitFor();
    assert.equal(await quality.getAttribute('data-quality'), 'unknown', 'Failed status refresh must not leave an available badge');
    fail = false; await quality.getByRole('button', { name: 'Retry live status' }).click();
    await quality.getByText('Source fetches are current', { exact: true }).waitFor();
    await quality.locator('summary').click();
    const canvas = page.getByRole('region', { name: 'Portfolio map' }); const box = await canvas.boundingBox();
    await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.6);
    await page.getByText('Browser fixture warning', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS unknown/fresh/failure/retry source states, one shared SSE with live.updated invalidation, honest power/proxy copy and live-alert hover');
  } finally {
    await browser.close(); for (const response of connections) response.end(); await new Promise(resolve => events.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
