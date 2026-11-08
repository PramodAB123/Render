// usage: node render.js <projectDir> [preview t1 t2 ...]
// Serves toon/ over http, loads <projectDir>/toon.json, draws every frame in headless Chromium -> <projectDir>/video.mp4
const {chromium} = require('playwright'); const fs = require('fs'), path = require('path'), http = require('http'); const {spawn} = require('child_process');
const ENG = __dirname, PROJ = path.resolve(process.argv[2] || '.'), mode = process.argv[3];
const srv = http.createServer((q, r) => { const f = path.join(ENG, decodeURIComponent(q.url.split('?')[0])); if (!f.startsWith(ENG) || !fs.existsSync(f)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, {'Content-Type': f.endsWith('.html') ? 'text/html' : 'application/octet-stream'}); fs.createReadStream(f).pipe(r); });
(async () => {
  await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
  const tl = JSON.parse(fs.readFileSync(path.join(PROJ, 'toon.json'), 'utf8'));
  const b = await chromium.launch({channel: (process.env.BROWSER_CHANNEL ?? 'msedge') || undefined});
  const p = await b.newPage({viewport: {width: 1080, height: 1920}}); p.on('pageerror', e => console.error('pageerror:', e.message));
  await p.goto(`http://localhost:${port}/toon.html`, {waitUntil: 'networkidle'}); await p.waitForFunction(() => window.ready); await p.evaluate(tl => window.init(tl), tl);
  const grab = t => p.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', .92); }, t);
  if (mode === 'preview') {
    for (const t of process.argv.slice(4).map(Number)) { const d = await grab(t); fs.writeFileSync(path.join(PROJ, `preview_${t}.jpg`), Buffer.from(d.split(',')[1], 'base64')); console.log('preview', t); }
  } else {
    const fps = 30, n = Math.ceil(tl.total * fps), t0 = Date.now();
    const ff = spawn(process.env.FFMPEG || 'ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '' + fps, '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', path.join(PROJ, 'video.mp4')], {stdio: ['pipe', 'inherit', 'inherit']});
    for (let i = 0; i < n; i++) { const d = await grab(i / fps); if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`  2d frame ${i}/${n}  ${((Date.now() - t0) / 1000 / (i + 1)).toFixed(2)}s/frame`); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close(); srv.close();
})();
