// Dependency-free browser smoke test using Chrome already on the Ubuntu runner.
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {readFile, mkdtemp, rm, mkdir, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {once} from 'node:events';

const site = resolve(process.argv[2] || '_site');
const live = process.argv[3] === '--live';
const output = resolve('portal-preview');
const prefix = '/security-twin-adapter-lab/';
const allowed = new Set(['index.html', 'ja/index.html', 'style.css', 'result.json', '.nojekyll']);
const server = createServer(async (req, res) => {
  const file = req.url === prefix ? 'index.html' : req.url === prefix + 'ja/' ? 'ja/index.html' : req.url.slice(prefix.length);
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
  const root = live ? `https://serevy.github.io${prefix}` : `http://127.0.0.1:${server.address().port}${prefix}`;
  if (live) {
    // CDN propagation may lag deployment. Fail closed if exact files never arrive.
    let matched = false;
    for (let attempt = 0; attempt < 12; attempt++) {
      matched = true;
      for (const path of ['index.html', 'ja/index.html', 'style.css', 'result.json']) {
        const response = await fetch(root + path, {cache: 'no-store', signal: AbortSignal.timeout(10000)});
        if (!response.ok || await response.text() !== await readFile(join(site, path), 'utf8')) { matched = false; break; }
      }
      if (matched) break;
      await delay(5000);
    }
    if (!matched) throw new Error('Live publication differs from the deployed artifact');
  }
  for (const locale of ['en', 'ja']) {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      await call('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
      await call('Page.navigate', {url: root + (locale === 'ja' ? 'ja/' : '')});
      let report;
      for (let i = 0; i < 50; i++) {
        const result = await call('Runtime.evaluate', {returnByValue: true, expression: `JSON.stringify({
          ready: document.readyState === 'complete' && document.documentElement.lang === ${JSON.stringify(locale)} && !!document.querySelector('.checks'),
          overflow: document.documentElement.scrollWidth > innerWidth,
          background: getComputedStyle(document.body).backgroundColor,
          checks: [...document.querySelectorAll('.checks tbody .badge')].map(x => x.textContent),
          heading: document.querySelector('h1')?.textContent,
          ids: [...document.querySelectorAll('.checks tbody tr')].map(x => x.dataset.scenario),
          provenance: [...document.querySelectorAll('.provenance dd')].map(x => x.textContent),
          provenanceLinks: [...document.querySelectorAll('.provenance a')].map(x => x.href),
          evidence: document.querySelector('[data-evidence-link]')?.href,
          stylesheet: document.querySelector('link[rel="stylesheet"]')?.href,
          languages: [...document.querySelectorAll('.language-switch a')].map(x => [x.lang, x.href, x.textContent, x.getAttribute('aria-current')]),
          links: [...document.querySelectorAll('a[href]')].map(x => x.getAttribute('href'))
        })`});
        if (!result.result?.value) { await delay(100); continue; }
        report = JSON.parse(result.result.value);
        if (report.ready) break;
        await delay(100);
      }
      if (!report?.ready || report.overflow || report.background !== 'rgb(246, 247, 243)') throw new Error(`${name}: layout or CSS failed`);
      if (JSON.stringify(report.checks) !== JSON.stringify(Object.values(expected.checks))) throw new Error(`${name}: displayed results mismatch`);
      if (JSON.stringify(report.ids) !== JSON.stringify(Object.keys(expected.checks))) throw new Error(`${locale}: scenario IDs changed`);
      if (expected.source) {
        const src = expected.source;
        if (!report.provenance[0]?.endsWith(' · ' + src.evidence_id) || report.provenance[3] !== src.updated_at || report.provenance[4] !== src.conclusion ||
            JSON.stringify(report.provenanceLinks) !== JSON.stringify([`https://github.com/serevy/security-twin-adapter-lab/actions/runs/${src.run_id}`, `https://github.com/serevy/security-twin-adapter-lab/commit/${src.head_sha}`])) throw new Error('Displayed provenance mismatch');
      } else if (report.provenance.length) throw new Error('Bootstrap must not claim provenance');
      if (report.evidence !== root + 'result.json' || report.stylesheet !== root + 'style.css') throw new Error('Locale-specific evidence or stylesheet');
      const languageLinks = [['en', root, 'English', locale === 'en' ? 'page' : null], ['ja', root + 'ja/', '日本語', locale === 'ja' ? 'page' : null]];
      if (JSON.stringify(report.languages) !== JSON.stringify(languageLinks)) throw new Error('Language switch mismatch');
      if (!report.heading.includes(locale === 'ja' ? '操作の範囲を限定。' : 'Bounded actions.')) throw new Error('Localized heading missing');
      const shared = await (await fetch(report.evidence)).json();
      if (JSON.stringify(shared) !== JSON.stringify(expected)) throw new Error('Shared evidence mismatch');
      for (const href of report.links) {
        const url = new URL(href, root + (locale === 'ja' ? 'ja/' : ''));
        if (url.origin === new URL(root).origin) {
          if (!(url.href === root + '#main' || url.href === root + 'ja/#main' || [root, root + 'ja/', root + 'result.json'].includes(url.href))) throw new Error('Unexpected local link destination');
          if (!(await fetch(url)).ok) throw new Error('Broken local link');
        } else if (!url.href.startsWith('https://github.com/serevy/security-twin-adapter-lab')) throw new Error('Unexpected external link destination');
      }
      const shot = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
      await writeFile(join(output, `${locale}-${name}.png`), Buffer.from(shot.data, 'base64'));
      console.log(`PASS ${live ? 'live' : 'local'} ${locale} ${name}: ${width}px, CSS loaded, no horizontal overflow, ${report.checks.length} matching statuses, provenance, shared JSON, project-subpath links`);
    }
  }
} finally {
  socket?.close();
  if (chrome.exitCode === null) chrome.kill('SIGKILL');
  await closed;
  server.close();
  await rm(profile, {recursive: true, force: true});
}
