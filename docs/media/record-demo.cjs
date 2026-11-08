// Records the real application in simulator mode. Requires Playwright, Chromium and FFmpeg.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { spawn } = require('node:child_process');
const { chromium } = createRequire(path.resolve(__dirname, '../../frontend/package.json'))('playwright');
const BASE = process.env.STORM_URL || 'http://127.0.0.1:5173';
const OUTPUT = process.env.STORM_VIDEO || path.join(__dirname, 'operation-storm-demo.mp4');
const RECORD = process.env.STORM_RECORD_VIDEO !== '0';
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined),
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'] });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, timezoneId: 'America/Chicago' });
  context.setDefaultTimeout(12000); await context.route('https://**/*', route => route.abort());
  const page = await context.newPage(); let activePage = page;
  const errors = []; context.on('page', popup => popup.on('pageerror', e => errors.push(e.message))); page.on('pageerror', e => errors.push(e.message));
  const api = async (endpoint, body) => {
    const response = await context.request.fetch(BASE + '/api' + endpoint, { method: body ? 'POST' : 'GET', data: body });
    assert(response.ok(), endpoint + ': ' + response.status()); return response.json();
  };
  let encoder, timer, capture = Promise.resolve(), busy = false, frames = 0;
  let recordingStarted = 0;
  const rawOutput = OUTPUT + '.capture.mp4';
  let encodeDone = Promise.resolve();
  const started = Date.now(); let resetAllowed = false;
  const caption = async text => {
    console.log(text);
    await activePage.evaluate(text => {
      let label = document.getElementById('demo-chapter');
      if (!label) { label = document.createElement('div'); label.id = 'demo-chapter'; document.body.append(label); }
      label.textContent = text + ' · Simulator / synthetic portfolio';
      Object.assign(label.style, { position: 'fixed', left: '430px', bottom: '12px', maxWidth: '900px', padding: '10px 14px',
        zIndex: '1000', background: '#123e2bef', border: '1px solid #b5d3bb', color: 'white', font: '14px system-ui', pointerEvents: 'none' });
    }, text);
    await activePage.waitForTimeout(RECORD ? 2500 : 150);
  };
  const view = async name => {
    await page.getByRole('navigation', { name: 'Portfolio tools' }).getByRole('button', { name, exact: true }).click();
    await page.getByRole('region', { name: 'Portfolio content' }).evaluate(element => { element.scrollTop = 0; });
  };
  try {
    assert.equal((await api('/messaging/status')).mode, 'sim', 'Use an isolated MESSAGING_MODE=sim instance'); resetAllowed = true;
    await api('/demo/reset', { scenario_id: 'harvey_houston' }); await page.goto(BASE);
    await page.waitForSelector('[data-map-ready="true"]');
    if (RECORD) {
      fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
      encoder = spawn(process.env.FFMPEG_PATH || 'ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '10', '-i', 'pipe:0',
        '-vf', 'scale=1280:800', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', rawOutput], { stdio: ['pipe', 'ignore', 'inherit'] });
      encodeDone = new Promise((resolve, reject) => { encoder.on('error', reject); encoder.on('close', code => code === 0 ? resolve() : reject(Error('FFmpeg exited ' + code))); });
      encoder.stdin.on('error', () => {});
      recordingStarted = Date.now();
      timer = setInterval(() => {
        if (busy) return; busy = true;
        capture = activePage.screenshot({ type: 'jpeg', quality: 80 }).then(buffer => { encoder.stdin.write(buffer); frames++; })
          .catch(() => {}).finally(() => { busy = false; });
      }, 100);
    }
    await caption('Plain-language explanations: hover the information icon');
    await page.getByRole('button', { name: 'About Estimated loss', exact: true }).first().hover();
    await page.getByRole('tooltip').waitFor();
    await page.waitForTimeout(1800);
    await page.keyboard.press('Escape');
    await page.mouse.move(700, 600, { steps: 10 });
    await caption('CBRE: see modeled loss and choose a response');
    await page.getByRole('main', { name: 'Map workspace' }).getByRole('button', { name: /Bayou Plaza/ }).click();
    const card = page.getByRole('region', { name: 'Building response actions' });
    await card.getByRole('button', { name: 'Approve response plan' }).waitFor();
    await caption('Approve a plan: costs, savings and an execution trail');
    await card.getByRole('button', { name: 'Approve response plan' }).click();
    await card.getByText('Execution in progress', { exact: true }).waitFor();
    const work = await api('/workorders?building_id=BLD-HOU-01'); assert(work.length && work.every(order => order.status === 'sent'));
    await view('Work Orders'); await caption('Photon workflow: setup tasks reach the demo inbox');
    await view('Texts');
    for (const order of work) {
      await page.getByLabel('Send as').selectOption(order.party_id);
      await page.getByLabel('Message', { exact: true }).fill('DONE ' + order.id);
      await page.getByRole('button', { name: 'Send simulated message', exact: true }).click();
      await page.waitForFunction(id => fetch('/api/workorders').then(r => r.json()).then(rows => rows.find(row => row.id === id)?.status === 'done'), order.id);
    }
    await card.getByText('Response completed', { exact: true }).waitFor();
    await caption('Technician replies complete work orders without reloading');
    await page.getByLabel('Send as').selectOption('resident'); await page.getByLabel('Resident phone').fill('+12145550123');
    await page.getByLabel('Message', { exact: true }).fill('Our apartment in Memorial flooded. 2 adults need shelter and a dry place.');
    await page.getByRole('button', { name: 'Send simulated message', exact: true }).click();
    await page.getByText('Message submitted. Responses and updates appear below.', { exact: true }).waitFor();
    await view('Help Sites'); await page.getByRole('heading', { name: 'Resident referrals', exact: true }).scrollIntoViewIfNeeded();
    assert((await api('/referrals'))[0].status === 'routed');
    await caption('State Farm: place residents at modeled safe sites with capacity');
    const activation = page.getByRole('article', { name: 'Help-site activation for Galleria Medical Offices' });
    await activation.getByRole('button', { name: 'Approve help-site activation' }).click();
    await activation.getByText(/Registered for routing/).waitFor();
    await caption('CBRE space adds 250 places and a tracked engineer setup task');
    await view('Reports'); await page.getByRole('button', { name: 'Generate executive summary', exact: true }).click();
    const link = page.getByRole('link', { name: 'Open printable report' }).first(); await link.waitFor();
    const popupPromise = context.waitForEvent('page'); await link.click(); const printable = await popupPromise;
    await printable.waitForLoadState(); activePage = printable; await caption('Share the financial outlook and response status');
    activePage = page; await printable.close();
    await page.getByRole('button', { name: 'Build simulation', exact: true }).click();
    const builder = page.getByRole('dialog', { name: 'Build a disaster simulation' });
    await builder.getByRole('button', { name: 'Pick a random city' }).click();
    await builder.getByLabel('Simulation disaster').selectOption('winter');
    await builder.getByRole('slider', { name: 'Minimum temperature' }).fill('-8');
    await builder.getByRole('slider', { name: 'Ice accumulation' }).fill('0.8');
    await builder.getByRole('slider', { name: 'Utility outage duration' }).fill('48');
    await caption('Build a hypothetical disaster: city, hazard and effect controls');
    await builder.getByRole('button', { name: 'Run custom simulation' }).click(); await builder.waitFor({ state: 'hidden' });
    await page.getByText('Custom simulation · hypothetical effects', { exact: true }).waitFor();
    await caption('The custom exercise uses the same loss and response engine');
    for (const [scenario, text] of [['uri_dallas', 'Winter Storm Uri: distinct snow and power-cascade view'], ['ian_fort_myers', 'Hurricane Ian: surge and wind motion, illustrative geometry']]) {
      await page.getByLabel('Disaster scenario').selectOption(scenario);
      await page.getByRole('navigation', { name: 'Disaster timeline' }).locator('button').filter({ has: page.locator('strong', { hasText: /^0h$/ }) }).click();
      await page.waitForFunction(() => document.querySelector('.storm-map')?.dataset.mapMoving === 'false'); await caption(text);
    }
    await caption('Restart the shared exercise from the app');
    await page.getByRole('button', { name: 'Restart current scenario', exact: true }).click();
    const restartDialog = page.getByRole('dialog', { name: 'Restart scenario?', exact: true });
    await restartDialog.getByRole('button', { name: 'Restart scenario', exact: true }).click();
    await restartDialog.waitFor({ state: 'hidden' });
    assert.equal((await api('/demo/state')).step_hour, (await api('/timeline'))[0].hour);
    assert.equal((await api('/workorders')).length, 0);
    await caption('Ready to run again: same scenario, clean starting point');
    assert.deepEqual(errors, []); assert(Date.now() - started < 210000, 'Demo must finish under 3:30');
    console.log('PASS repeatable demo flow in ' + ((Date.now() - started) / 1000).toFixed(1) + ' seconds');
  } finally {
    try {
      clearInterval(timer); await capture;
      if (encoder) {
        encoder.stdin.end(); await encodeDone;
        const scale = ((Date.now() - recordingStarted) / 1000) / (frames / 10);
        await new Promise((resolve, reject) => {
          const normalize = spawn(process.env.FFMPEG_PATH || 'ffmpeg', ['-y', '-loglevel', 'error', '-i', rawOutput,
            '-vf', `setpts=${scale.toFixed(6)}*PTS`, '-r', '10', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUTPUT], { stdio: ['ignore', 'ignore', 'inherit'] });
          normalize.on('error', reject); normalize.on('close', code => code === 0 ? resolve() : reject(Error('Video normalization exited ' + code)));
        });
        fs.unlinkSync(rawOutput); console.log('Video frames: ' + frames + '; output: ' + OUTPUT);
      }
    } finally {
      if (resetAllowed) await api('/demo/reset', { scenario_id: 'harvey_houston' }).catch(() => {});
      await browser.close();
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
