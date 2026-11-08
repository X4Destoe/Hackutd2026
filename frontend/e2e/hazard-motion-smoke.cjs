// Real scenario geometry; resets an isolated simulator instance.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1000 }, reducedMotion: 'no-preference' });
  context.setDefaultTimeout(8000);
  await context.route('https://**/*', route => route.abort());
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const api = async (path, body) => {
    const response = await context.request.fetch(BASE + '/api' + path, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), `${path}: ${response.status()}`); return response.json();
  };
  const pixels = () => page.locator('.storm-hazard-motion').evaluate(canvas => {
    const bytes = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0, hash = 0;
    for (let i = 3; i < bytes.length; i += 4) if (bytes[i]) { count++; hash = (hash + i * bytes[i]) % 1000000007; }
    return { count, hash, particles: Number(canvas.dataset.particleCount), frame: canvas.dataset.frame };
  });
  let resetAllowed = false;
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim'); resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'uri_dallas' });
    await api('/timeline', { hour: 0 });
    await page.goto(BASE);
    await page.waitForFunction(() => document.querySelector('.storm-hazard-motion')?.dataset.motionStyles.includes('snow_ice'));
    await page.waitForTimeout(400);
    const first = await pixels(); await page.waitForTimeout(250); const second = await pixels();
    assert(first.count > 0 && second.count > 0 && first.hash !== second.hash, 'Snow must actually paint and move');
    assert(second.particles <= 300 && second.particles > 0);
    await page.screenshot({ path: '/tmp/storm-snow-motion.png' });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForFunction(() => document.querySelector('.storm-hazard-motion')?.dataset.reducedMotion === 'true');
    assert.equal((await pixels()).count, 0, 'Reduced motion must clear particles');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.waitForFunction(() => document.querySelector('.storm-hazard-motion')?.dataset.reducedMotion === 'false');
    await page.waitForTimeout(200); assert((await pixels()).count > 0, 'Motion must resume when preference changes');
    await page.getByRole('checkbox', { name: 'Hazard overlay' }).uncheck();
    assert.equal(await page.locator('.storm-hazard-motion').count(), 0);
    await page.getByRole('checkbox', { name: 'Hazard overlay' }).check();
    for (const [scenario, styles] of [['ian_fort_myers', ['surge_water', 'wind_swirl']], ['harvey_houston', ['wind_swirl']]]) {
      await api(`/scenarios/${scenario}/load`, {}); await api('/timeline', { hour: 0 });
      await page.waitForFunction(expected => expected.every(style => document.querySelector('.storm-hazard-motion')?.dataset.motionStyles.includes(style)), styles);
      await page.waitForTimeout(400);
      const state = await pixels(); assert(state.count > 0 && state.particles <= 300);
      assert.equal(await page.locator('.storm-hazard-motion').count(), 1, 'Scenario switches must not leak canvases');
      if (scenario === 'ian_fort_myers') await page.screenshot({ path: '/tmp/storm-surge-motion.png' });
    }
    await page.getByRole('main', { name: 'Map workspace' }).getByRole('button', { name: /Bayou Plaza ·/ }).click();
    await page.getByRole('region', { name: 'Building response actions' }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS real snow/surge/wind geometry paints moving particles; <=300 particles, live reduced-motion toggle, hazard toggle, no leaked canvas or blocked building clicks');
  } finally {
    if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
