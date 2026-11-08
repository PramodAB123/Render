// usage: node hf_render.js <workDir> <out.mp4> <seconds>
// Renders a claude-animation-skills "quick skill" page (breakdown, graph, map-route ...) without HyperFrames:
// it serves the prepared folder, waits for the page's build promises, then for every frame sends the
// page's own 'hf-seek' event (and seeks any registered GSAP timelines) and screenshots the page.
const {chromium} = require('playwright'); const fs = require('fs'), path = require('path'), http = require('http'); const {spawn} = require('child_process');
const DIR = path.resolve(process.argv[2]), OUT = process.argv[3], SECS = parseFloat(process.argv[4] || '4.2'), FPS = 30;
const TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.json': 'application/json'};
const srv = http.createServer((q, r) => { const f = path.join(DIR, decodeURIComponent(q.url.split('?')[0])); if (!f.startsWith(DIR) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, {'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream'}); fs.createReadStream(f).pipe(r); });
(async () => {
  await new Promise(r => srv.listen(0, r));
  const b = await chromium.launch({channel: (process.env.BROWSER_CHANNEL ?? 'msedge') || undefined, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
  const p = await b.newPage({viewport: {width: 1080, height: 1920}}); p.on('pageerror', e => console.error('pageerror:', e.message));
  await p.goto(`http://localhost:${srv.address().port}/index.html`, {waitUntil: 'networkidle'});
  await p.waitForFunction(() => window.__hf && window.__hf.buildReady, null, {timeout: 60000}).catch(() => {});
  await p.evaluate(async () => { const r = (window.__hf && window.__hf.buildReady) || {}; await Promise.all(Object.values(r)); });
  const n = Math.round(SECS * FPS), t0 = Date.now();
  const ff = spawn(process.env.FFMPEG || 'ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '' + FPS, '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', OUT], {stdio: ['pipe', 'inherit', 'inherit']});
  for (let i = 0; i < n; i++) {
    await p.evaluate(t => { window.dispatchEvent(new CustomEvent('hf-seek', {detail: {time: t}})); for (const tl of Object.values(window.__timelines || {})) { try { tl.seek(t, false); } catch (e) {} } }, i / FPS);
    const buf = await p.screenshot({type: 'jpeg', quality: 92});
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log(`  breakdown clip: ${n} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await b.close(); srv.close();
})();
