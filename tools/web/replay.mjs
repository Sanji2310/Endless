// Replays a recorded GLES stream (see tools/web/gles.js) in headless Chromium and saves every presented frame.
// usage: node tools/web/replay.mjs <gles.bin> <outDir> <width> <height>
import fs from 'fs';
import http from 'http';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }

const [stream, outDir, w = '540', h = '960'] = process.argv.slice(2);
const webDir = path.dirname(new URL(import.meta.url).pathname);
fs.mkdirSync(outDir, { recursive: true });
const browser = await playwright.chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
// served over a local HTTP server: fulfilling a large recording through page.route crashes the page
const server = http.createServer((req, res) => {
  const name = new URL(req.url, 'http://x').pathname.slice(1);
  const f = name === 'gles.bin' ? stream : path.join(webDir, name);
  if (!fs.existsSync(f)) { res.writeHead(404); res.end('missing ' + name); return; }
  const type = name.endsWith('.html') ? 'text/html' : name.endsWith('.js') ? 'application/javascript' : 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': type, 'Content-Length': fs.statSync(f).size });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
await page.goto(`http://127.0.0.1:${server.address().port}/replay.html?w=${w}&h=${h}`);
await page.waitForFunction('window.ready === true || window.error', null, { timeout: 1800000, polling: 500 });
const err = await page.evaluate('window.error');
if (err) { console.error(err); await browser.close(); process.exit(1); }
const frames = await page.evaluate('window.frames');
for (const [name, url] of frames) {
  const file = path.join(outDir, name + '.png');
  fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  console.log('wrote', file);
}
await browser.close();
server.close();
