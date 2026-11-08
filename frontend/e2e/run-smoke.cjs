// Browser gates mutate one shared demo workspace: always run them serially.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const checks = ['site-controls', 'map', 'execution', 'action-screens', 'community-activation',
  'message-followup', 'hazard-motion', 'live-status', 'simulation'];

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 1 && args[0] === '--list') {
    console.log(checks.join('\n'));
    return;
  }
  const selected = args.length ? args : checks;
  for (const name of selected) if (!checks.includes(name)) throw new Error(`Unknown check: ${name}. Use --list.`);
  const base = new URL(process.env.STORM_URL || 'http://127.0.0.1:5173').origin;
  const response = await fetch(`${base}/api/messaging/status`, { signal: AbortSignal.timeout(10000) });
  if (!response.ok || (await response.json()).mode !== 'sim') {
    throw new Error('Checks require MESSAGING_MODE=sim. No demo mutations were started.');
  }
  const { chromium } = require('playwright');
  const executable = process.env.CHROMIUM_PATH ||
    (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : chromium.executablePath());
  if (!fs.existsSync(executable)) throw new Error('Chromium is missing. Run npm run test:e2e:install or set CHROMIUM_PATH.');
  const lock = path.join(os.tmpdir(), `storm-browser-${crypto.createHash('sha256').update(base).digest('hex').slice(0, 16)}.lock`);
  try { fs.mkdirSync(lock); }
  catch (error) {
    if (error.code === 'EEXIST') throw new Error(`Another browser gate may be using ${base}. Stop it before removing stale lock ${lock}.`);
    throw error;
  }
  let child;
  const stop = signal => {
    child?.kill(signal);
    process.exitCode = signal === 'SIGINT' ? 130 : 143;
  };
  const interrupt = () => stop('SIGINT');
  const terminate = () => stop('SIGTERM');
  process.on('SIGINT', interrupt); process.on('SIGTERM', terminate);
  const started = Date.now();
  try {
    console.log(`Simulator verified. Running ${selected.length} browser checks serially against ${base}.`);
    for (const name of selected) {
      if (process.exitCode) break;
      console.log(`\n[${name}]`);
      const result = await new Promise((resolve, reject) => {
        child = spawn(process.execPath, [path.join(__dirname, `${name}-smoke.cjs`)], {
          stdio: 'inherit', env: { ...process.env, STORM_URL: base, CHROMIUM_PATH: executable },
          timeout: 180000, killSignal: 'SIGTERM',
        });
        child.once('error', reject);
        child.once('exit', (code, signal) => resolve({ code, signal }));
      });
      child = undefined;
      if (result.code !== 0) throw new Error(`${name} failed (${result.signal || result.code}). Remaining checks were not run.`);
    }
    if (!process.exitCode) console.log(`\nPASS ${selected.length} browser checks in ${((Date.now() - started) / 1000).toFixed(1)}s.`);
  } finally {
    process.off('SIGINT', interrupt); process.off('SIGTERM', terminate);
    fs.rmSync(lock, { recursive: true, force: true });
  }
}
main().catch(error => {
  console.error(`Browser acceptance failed: ${error.message}`);
  process.exitCode ||= 1;
});
