// Headless WebGL preview: renders every frame in frames.bin with the game's shaders and saves PNGs.
// usage: node tools/web/run.mjs <dataDir with pongo.bin, frames.bin, shaders.json> <outDir> [prefix]
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const [dataDir, outDir, prefix = 'frame'] = process.argv.slice(2);
const webDir = path.dirname(new URL(import.meta.url).pathname);
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1200, height: 2200 } });
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
await page.route('http://pongo.local/**', route => {
  const name = new URL(route.request().url()).pathname.slice(1);
  const f = ['pongo.bin', 'frames.bin', 'shaders.json'].includes(name) ? path.join(dataDir, name) : path.join(webDir, name);
  if (!fs.existsSync(f)) return route.fulfill({ status: 404, body: 'missing ' + name });
  const type = name.endsWith('.html') ? 'text/html' : name.endsWith('.js') ? 'application/javascript' : name.endsWith('.json') ? 'application/json' : 'application/octet-stream';
  route.fulfill({ status: 200, body: fs.readFileSync(f), contentType: type });
});
await page.goto('http://pongo.local/index.html');
await page.waitForFunction('window.ready === true || window.error', null, { timeout: 900000 });
const err = await page.evaluate('window.error');
if (err) { console.error(err); process.exit(1); }
const n = await page.evaluate('window.frameCount');
for (let i = 0; i < n; i++) {
  const t0 = Date.now();
  const res = await page.evaluate(i => { try { return window.renderFrame(i); } catch (e) { return String(e.stack || e); } }, i);
  if (res !== true) { console.error('frame', i, res); process.exit(1); }
  const file = path.join(outDir, `${prefix}_${String(i).padStart(4, '0')}.png`);
  await page.locator('#c').screenshot({ path: file });
  console.log('rendered', file, (Date.now() - t0) + 'ms');
}
await browser.close();
