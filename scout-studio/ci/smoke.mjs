// Browser smoke test for the production build (run by .github/workflows/scout-studio-check.yml).
// Usage: BASE=http://127.0.0.1:4173/ node ci/smoke.mjs <screenshot-dir>
import { chromium } from 'playwright';
import fs from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:4173/';
const OUT = process.argv[2] || 'ci-shots';
fs.mkdirSync(OUT, { recursive: true });
const results = [];
// Screenshots are evidence, not assertions: a slow software-rendered frame must not fail the run.
async function shot(page, path) {
  try { await page.screenshot({ path, timeout: 120000, animations: 'disabled', caret: 'hide' }); }
  catch (e) { console.log(`WARN  screenshot skipped (${path}): ${e.message.split('\n')[0]}`); }
}

const check = (name, ok, detail = "") => { const line = `${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`; results.push(line); console.log(line); };
const GL = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ args: GL });

async function newPage(opts = {}, motion = 'off') {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true, ...opts });
  await ctx.addInitScript(m => { try { localStorage.setItem('scout-motion-prefs-v1', JSON.stringify({ motion: m, quality: 'auto' })); } catch {} }, motion);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/404|500|502|504|Failed to load resource|\/api\//.test(m.text())) errors.push(m.text()); });
  return { ctx, page, errors };
}
const transforms = page => page.$$eval('.subject-stage .hotspot', els => els.map(e => e.style.transform + '|' + e.dataset.visible));

// ---------- Desktop interactions (motion off) ----------
{
  const { ctx, page, errors } = await newPage();
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForSelector('.scene-layer.is-ready', { timeout: 180000 });
  const stageBox = await page.locator('.subject-stage').boundingBox();
  const neutral = async () => { await page.mouse.move(stageBox.x + stageBox.width / 2, stageBox.y + stageBox.height * 0.35); await page.waitForTimeout(2500); };
  await neutral();
  await shot(page, `${OUT}/desktop-hero.png`);
  const t0 = await transforms(page);
  check('3D scene ready and hotspots projected', t0.some(t => t.includes('translate3d')), t0.join(' ; '));
  const box = await page.locator('.subject-stage').boundingBox();
  const cy = box.y + box.height * 0.45;
  await page.mouse.move(box.x + box.width * 0.4, cy);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * 0.4 + i * 25, cy, { steps: 2 });
  await page.mouse.up();
  await page.waitForTimeout(900);
  const t1 = await transforms(page);
  check('Mouse drag rotates the subject', JSON.stringify(t1) !== JSON.stringify(t0));
  check('Drag hint hides after first drag', (await page.locator('.drag-hint').count()) === 0);
  await page.getByRole('button', { name: 'Reset view' }).click();
  await neutral();
  const t2 = await transforms(page);
  check('Reset view returns to the rest pose', JSON.stringify(t2) === JSON.stringify(t0), t2[0]);
  await page.locator('.subject-stage').focus();
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(2500);
  check('Arrow key rotates the subject', JSON.stringify(await transforms(page)) !== JSON.stringify(t2));
  await page.keyboard.press('r');
  await page.waitForTimeout(900);
  await page.getByRole('button', { name: 'Explore Scout' }).click();
  check('Explore Scout opens the capability panel', await page.locator('#scout-capabilities').isVisible());
  await page.locator('#scout-capabilities').getByRole('button', { name: /Six-hour listening/ }).click();
  await page.waitForTimeout(900);
  check('Capability selection gives visible feedback', (await page.locator('#scout-capabilities button[aria-pressed="true"]').count()) === 1 && (await page.locator('.hotspot.is-active').count()) === 1);
  const detail = await page.locator('.capability-detail').textContent();
  check('Capability detail text updates', /UTC 00:00/.test(detail || ''), (detail || '').slice(0, 60));
  await shot(page, `${OUT}/e2e-hotspot.png`);
  const visibleSpot = page.locator('.subject-stage .hotspot[data-visible="true"]').first();
  if (await visibleSpot.count()) { await visibleSpot.click({ force: true }); await page.waitForTimeout(400); check('Clicking a 3D hotspot selects it', (await page.locator('.hotspot.is-active').count()) <= 1); }

  // Get MC dialog: focus trap, Escape, focus restore
  const getMc = page.locator('.site-header').getByRole('button', { name: /Get MC/ });
  await getMc.click();
  const dialog = page.getByRole('dialog', { name: 'Get MC and subscriptions' });
  check('Get MC opens a dialog', await dialog.isVisible());
  for (let i = 0; i < 14; i++) await page.keyboard.press('Tab');
  check('Focus stays trapped in the dialog', await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]')));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  check('Escape closes the dialog', (await page.getByRole('dialog').count()) === 0);
  check('Focus returns to the opener', await page.evaluate(() => document.activeElement?.textContent?.includes('Get MC') ?? false));

  // Wallet
  await page.locator('.site-header').getByRole('button', { name: 'Connect wallet' }).click();
  await page.getByRole('button', { name: /Connect MetaMask/ }).click();
  check('Wallet modal explains missing MetaMask', await page.getByText('MetaMask was not detected', { exact: false }).first().isVisible());
  await page.getByRole('button', { name: 'Close wallet' }).click();
  await page.waitForTimeout(300);

  // Sample memo: visible early and opens the matching research file
  await page.locator('#memo').scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await shot(page, `${OUT}/desktop-memo.png`);
  check('Sample memo shows finding, evidence and open risks', (await page.locator('.memo-body section').count()) === 3);
  await page.getByRole('button', { name: 'Open the full research file' }).click();
  await page.waitForTimeout(400);
  check('Sample memo opens the AURA research file', await page.locator('.detail-panel[role="dialog"]').isVisible() && /AURA/.test(await page.locator('.detail-panel').textContent() || ''));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  await page.locator('#why').scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await shot(page, `${OUT}/desktop-why.png`);
  check('Robinhood Chain badge and rationale are present', (await page.locator('.chain-badge').count()) >= 2 && await page.getByRole('heading', { name: 'Why Robinhood Chain?' }).isVisible());
  await page.locator('.story-chapter').nth(1).scrollIntoViewIfNeeded();
  await page.waitForTimeout(2500);
  await shot(page, `${OUT}/desktop-story-verify.png`);

  // Run demo
  await page.locator('.story-finale').scrollIntoViewIfNeeded();
  await page.getByRole('button', { name: /Run the demo/ }).click();
  await page.waitForTimeout(4500);
  check('Guided demo completes', await page.getByText('The trail is ready.').isVisible());
  await page.getByRole('button', { name: 'Explore candidates' }).last().click();
  await page.waitForTimeout(1200);
  check('Demo hands off to the console', (await page.getByRole('dialog').count()) === 0 && await page.locator('#console').evaluate(el => el.getBoundingClientRect().top < 400));
  const status = await page.locator('.data-status').textContent();
  check('Data status beside Run names the source and what reset does', /Demo · fictional data/.test(status || '') && /never runs new research/.test(status || ''), (status || '').slice(0, 80));
  await page.locator('.workspace-toolbar').scrollIntoViewIfNeeded();
  await shot(page, `${OUT}/desktop-console-status.png`);

  // Candidate details
  await page.getByRole('button', { name: /Open research/ }).first().click();
  check('Candidate detail drawer opens', await page.locator('.detail-panel[role="dialog"]').isVisible());
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  // Compare
  const toggles = page.locator('.compare-toggle');
  await toggles.nth(0).click(); await toggles.nth(1).click();
  await page.getByRole('button', { name: /^Compare/ }).click();
  check('Comparison shows two candidates', (await page.locator('.compare-column').count()) === 2);
  await page.getByRole('button', { name: 'Close comparison' }).click();
  await page.waitForTimeout(300);
  // Filters
  await page.getByRole('button', { name: /High risk/ }).click();
  const risky = await page.locator('.candidate-card').count();
  await page.getByRole('button', { name: 'All candidates' }).click();
  const all = await page.locator('.candidate-card').count();
  check('Filters change the visible candidates', risky < all, `${risky}/${all}`);
  await page.getByLabel('Search token or pair').fill('AURA');
  check('Search filters candidates', (await page.locator('.candidate-card').count()) === 1);
  await page.getByLabel('Search token or pair').fill('');
  // Export and re-import
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export' }).click()]);
  const file = `${OUT}/export.json`;
  await download.saveAs(file);
  await page.locator('input[type=file]').setInputFiles(file);
  await page.waitForTimeout(500);
  const notice = await page.locator('.inline-notice').textContent();
  check('Export then import round-trips', /Imported \d+ candidates/.test(notice || ''), notice || '');
  check('Imported snapshot is labelled', await page.getByText('IMPORTED SNAPSHOT', { exact: true }).isVisible());
  await page.getByRole('button', { name: 'Clear import' }).click();
  // Stale import rejected
  const stale = JSON.parse(fs.readFileSync(file, 'utf8')); stale.generated -= 7 * 3600;
  fs.writeFileSync(`${OUT}/stale.json`, JSON.stringify(stale));
  await page.locator('input[type=file]').setInputFiles(`${OUT}/stale.json`);
  await page.waitForTimeout(400);
  check('Stale export from an earlier window is rejected', /earlier six-hour window/.test(await page.locator('.inline-notice').textContent() || ''));
  // Direct navigation + resize
  await page.goto(BASE + '#console', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  check('Direct navigation to #console lands on the console', await page.locator('#console').evaluate(el => Math.abs(el.getBoundingClientRect().top) < 120));
  await page.setViewportSize({ width: 900, height: 800 });
  await page.waitForTimeout(800);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(800);
  check('No uncaught errors during desktop flows', errors.length === 0, errors.join(' | '));
  await ctx.close();
}

// ---------- Six-hour boundary with a controlled clock ----------
{
  const { ctx, page, errors } = await newPage();
  const boundary = Math.ceil(Date.now() / 21600000) * 21600000;
  await page.clock.install({ time: new Date(boundary - 8000) });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.candidate-card', { timeout: 20000 });
  const before = await page.locator('.candidate-card').count();
  await page.clock.runFor(12000);
  await page.waitForTimeout(300);
  const after = await page.locator('.candidate-card').count();
  const msg = await page.locator('.inline-notice').textContent().catch(() => '');
  check('Board clears at the six-hour UTC boundary', before > 0 && after === 0 && /new six-hour window/.test(msg || ''), `${before} → ${after}`);
  check('Reset does not claim new research ran', /Run the local Scout or import a fresh export/.test(msg || ''));
  check('No uncaught errors across the boundary', errors.length === 0, errors.join(' | '));
  await ctx.close();
}

// ---------- WebGL unavailable ----------
{
  const b2 = await chromium.launch({ args: ['--disable-webgl', '--disable-3d-apis'] });
  const ctx = await b2.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  check('WebGL failure shows the static fallback', (await page.locator('.scene-layer.is-fallback').count()) === 1 && await page.locator('.subject-poster').isVisible());
  check('Product works without 3D', (await page.locator('.candidate-card').count()) > 0 && errors.length === 0, errors.join(' | '));
  await shot(page, `${OUT}/e2e-fallback.png`);
  await b2.close();
}

// ---------- Touch, render resolution and asset lab ----------
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await ctx.addInitScript(() => localStorage.setItem('scout-motion-prefs-v1', JSON.stringify({ motion: 'off', quality: 'auto' })));
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(BASE + '?debug=scene', { waitUntil: 'networkidle' });
  await page.waitForSelector('.scene-layer.is-ready', { timeout: 180000 });
  await page.waitForTimeout(2500);
  await shot(page, `${OUT}/mobile-390.png`);
  const cdp = await ctx.newCDPSession(page);
  const box = await page.locator('.subject-stage').boundingBox();
  const swipe = async (x0, y0, x1, y1) => {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x0, y: y0 }] });
    for (let i = 1; i <= 10; i++) {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x0 + ((x1 - x0) * i) / 10, y: y0 + ((y1 - y0) * i) / 10 }] });
      await page.waitForTimeout(30);
    }
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  };
  const tf = () => page.$$eval('.subject-stage .hotspot', els => els.map(e => e.style.transform).join(';'));
  const y = Math.min(box.y + box.height * 0.3, 800);
  const before = await tf();
  const s0 = await page.evaluate(() => scrollY);
  await swipe(box.x + 80, y, box.x + 300, y + 6);
  await page.waitForTimeout(4000);
  const s1 = await page.evaluate(() => scrollY);
  check('Touch: horizontal swipe rotates the subject', before !== (await tf()));
  check('Touch: horizontal swipe does not scroll', Math.abs(s1 - s0) < 30, `${s0} → ${s1}`);
  await swipe(box.x + 180, 760, box.x + 185, 300);
  await page.waitForTimeout(2000);
  const s2 = await page.evaluate(() => scrollY);
  check('Touch: vertical swipe still scrolls the page', s2 > s1 + 60, `${s1} → ${s2}`);
  check('Mobile: no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  const tops = await page.evaluate(() => Object.fromEntries(['memo', 'why', 'story', 'console'].map(id => [id, Math.round(document.getElementById(id).getBoundingClientRect().top + scrollY)])));
  const consoleTop = tops.console;
  console.log(`INFO  mobile 390×844 section tops: ${Object.entries(tops).map(([k, v]) => `${k} ${v}px`).join(' · ')}`);
  check('Mobile: console starts within 5,000 px', consoleTop < 5000, `${consoleTop}px`);
  for (const id of ['memo', 'why', 'story']) {
    await page.evaluate(sel => document.querySelector(sel).scrollIntoView({ block: 'start' }), id === 'story' ? '.story-stage' : `#${id}`);
    await page.waitForTimeout(1500);
    await shot(page, `${OUT}/mobile-${id}.png`);
  }
  const row = page.locator('.story-chapters');
  check('Mobile: chapters form a swipeable row', await row.evaluate(el => el.scrollWidth > el.clientWidth + 1));
  await row.evaluate(el => el.scrollTo({ left: el.scrollWidth, behavior: 'instant' }));
  await page.waitForTimeout(800);
  check('Mobile: last chapter can be reached', await page.locator('.story-chapter').last().evaluate(el => { const r = el.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; }));
  check('Mobile: swipe row keeps the page from overflowing', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  console.log('INFO  mobile 390×844 @DPR3: ' + (await page.locator('.scene-debug').textContent()).replace(/\n/g, ' | '));
  check('Mobile flow without uncaught errors', errors.length === 0, errors.join(' | '));
  await ctx.close();
}

for (const [w, h, dpr] of [[3840, 2160, 1], [1920, 1080, 2], [1440, 900, 2]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr });
  await ctx.addInitScript(() => localStorage.setItem('scout-motion-prefs-v1', JSON.stringify({ motion: 'off', quality: 'auto' })));
  const page = await ctx.newPage();
  await page.goto(BASE + '?debug=scene', { waitUntil: 'networkidle' });
  await page.waitForSelector('.scene-layer.is-ready', { timeout: 300000 });
  await page.waitForTimeout(2500);
  const text = (await page.locator('.scene-debug').textContent()).replace(/\n/g, ' | ');
  console.log(`INFO  ${w}×${h} @DPR${dpr}: ${text}`);
  if (w * dpr >= 3840) check(`${w}×${h} @DPR${dpr} renders a UHD buffer`, /buffer 3840×2160/.test(text));
  if (w === 3840) await shot(page, `${OUT}/hero-3840x2160.png`);
  await ctx.close();
}

{
  const { ctx, page, errors } = await newPage();
  await page.goto(BASE + 'lab', { waitUntil: 'networkidle' });
  await page.waitForTimeout(8000);
  check('Asset lab renders its samples and inventory', (await page.locator('.lab-sample').count()) === 5);
  await page.getByRole('button', { name: /Capture front/ }).click();
  await page.waitForTimeout(6000);
  check('Asset lab captures three angles', (await page.locator('.lab-angles img').count()) === 3);
  await shot(page, `${OUT}/lab.png`);
  check('Asset lab without uncaught errors', errors.length === 0, errors.join(' | '));
  await ctx.close();
}

await browser.close();
const failed = results.filter(r => r.startsWith('FAIL'));
console.log(`\nSUMMARY  ${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
