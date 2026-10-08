// Dependency-free browser smoke test using Chrome already on the Ubuntu runner.
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {readFile, mkdtemp, rm, mkdir, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {once} from 'node:events';

const site = resolve(process.argv[2] || '_site');
const output = resolve('portal-preview');
const prefix = '/security-twin-adapter-lab/';
const allowed = new Set(['index.html', 'style.css', 'result.json', '.nojekyll']);
const server = createServer(async (req, res) => {
  const file = req.url === prefix ? 'index.html' : req.url.slice(prefix.length);
  if (!req.url.startsWith(prefix) || !allowed.has(file)) {
    res.writeHead(404).end(); return;
  }
  try {
    res.setHeader('Content-Type', file.endsWith('.css') ? 'text/css' : file.endsWith('.json') ? 'application/json' : 'text/html');
    res.end(await readFile(join(site, file)));
  } catch { res.writeHead(404).end(); }
});
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const profile = await mkdtemp(join(tmpdir(), 'portal-chrome-'));
const chrome = spawn(process.env.CHROME || 'google-chrome', ['--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
let chromeDiagnostic = '';
chrome.stderr.on('data', data => { chromeDiagnostic = (chromeDiagnostic + data.toString()).slice(-4000); });
const closed = new Promise(resolve => chrome.once('close', resolve));
let launchError;
chrome.on('error', error => { launchError = error; });
let socket;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  let port;
  for (let i = 0; i < 100; i++) {
    if (launchError) throw launchError;
    if (chrome.exitCode !== null) throw new Error(`Chrome exited (${chrome.exitCode}): ${chromeDiagnostic}`);
    try { port = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break; }
    catch { await delay(100); }
  }
  if (!port) throw new Error(`Chrome readiness timeout: ${chromeDiagnostic}`);
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    const entry = pending.get(message.id);
    if (entry) {
      clearTimeout(entry.timeout); pending.delete(message.id);
      message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);
    }
  };
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    const timeout = setTimeout(() => { pending.delete(key); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
    pending.set(key, {resolve, reject, timeout}); socket.send(JSON.stringify({id: key, method, params}));
  });
  await call('Page.enable');
  await mkdir(output, {recursive: true});
  const expected = JSON.parse(await readFile(join(site, 'result.json'), 'utf8'));
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
    await call('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
    await call('Page.navigate', {url: `http://127.0.0.1:${server.address().port}${prefix}`});
    let report;
    for (let i = 0; i < 50; i++) {
      const result = await call('Runtime.evaluate', {returnByValue: true, expression: `JSON.stringify({
        ready: document.readyState === 'complete' && !!document.querySelector('.checks'),
        overflow: document.documentElement.scrollWidth > innerWidth,
        background: getComputedStyle(document.body).backgroundColor,
        checks: [...document.querySelectorAll('.checks tbody .badge')].map(x => x.textContent.replace(' ', '_')),
        heading: document.querySelector('h1')?.textContent,
        links: [...document.querySelectorAll('a[href]')].map(x => x.getAttribute('href'))
      })`});
      if (!result.result?.value) { await delay(100); continue; }
      report = JSON.parse(result.result.value);
      if (report.ready) break;
      await delay(100);
    }
    if (!report?.ready || report.overflow || report.background !== 'rgb(246, 247, 243)') throw new Error(`${name}: layout or CSS failed`);
    if (JSON.stringify(report.checks) !== JSON.stringify(Object.values(expected.checks))) throw new Error(`${name}: displayed results mismatch`);
    for (const href of report.links) {
      if (!(href === '#main' || href === './' || href === 'result.json' || href.startsWith('https://github.com/serevy/security-twin-adapter-lab'))) throw new Error('Unexpected link destination');
    }
    const shot = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
    await writeFile(join(output, `${name}.png`), Buffer.from(shot.data, 'base64'));
    console.log(`PASS ${name}: ${width}px, CSS loaded, no horizontal overflow, ${report.checks.length} matching statuses, project-subpath links`);
  }
} finally {
  socket?.close();
  if (chrome.exitCode === null) chrome.kill('SIGKILL');
  await closed;
  server.close();
  await rm(profile, {recursive: true, force: true});
}
