// node tools/icon/make_icon.mjs [bust.png]  ->  res/mipmap-*/ic_launcher.png (+ renders/design/icon_512.png)
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }
const here = path.dirname(new URL(import.meta.url).pathname), repo = path.resolve(here, '../..');
const bust = path.resolve(process.argv[2] || path.join(repo, 'renders/design/icon_bust.png'));
const browser = await playwright.chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.goto(`file://${here}/compose.html`);
await page.waitForFunction('window.ready === true');
const out = await page.evaluate(src => window.compose(src), 'data:image/png;base64,' + fs.readFileSync(bust).toString('base64'));
const dirs = { 48: 'mdpi', 72: 'hdpi', 96: 'xhdpi', 144: 'xxhdpi', 192: 'xxxhdpi' };
for (const [n, url] of Object.entries(out)) {
  const file = dirs[n] ? path.join(repo, 'res', 'mipmap-' + dirs[n], 'ic_launcher.png') : path.join(repo, 'renders/design/icon_512.png');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  console.log('wrote', path.relative(repo, file));
}
await browser.close();
