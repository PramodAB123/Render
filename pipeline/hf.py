"""HyperFrames (heygen-com/hyperframes, Apache-2.0, free) as the frame renderer for the 2d and stick engines.
Both engines are canvas animations that draw any frame from its time alone, so they follow HyperFrames' seek
protocol: a root composition with data-duration/data-fps, a build-ready promise, and an 'hf-seek' listener that
draws the frame. HyperFrames then captures every frame deterministically with parallel Chrome workers and encodes it.
If HyperFrames is missing or fails, the caller falls back to its own Playwright frame loop."""
import json, os, re, shutil, subprocess
from common import ROOT, FFMPEG

HF_VERSION = "0.9.26"


def available():
    """Opt-in only (RENDERER=hyperframes or config video.renderer). HyperFrames screenshots the whole page for every
    frame: on GitHub's runners (no GPU) that measured ~2 s/frame, 109 min for a 110 s video, while the built-in
    renderers read the canvas directly at ~0.1-0.3 s/frame. So the built-in renderers are the default."""
    from common import load_config
    want = os.environ.get("RENDERER") or load_config()["video"].get("renderer", "builtin")
    return want == "hyperframes" and (ROOT / "node_modules" / "hyperframes" / "package.json").exists()


def render(project_dir, out_mp4, fps=30):
    """npx hyperframes render <dir> -> out_mp4 (high quality; the final mix re-encodes at a sensible bitrate)."""
    env = dict(os.environ, HYPERFRAMES_RENDER_LOCK="off", DO_NOT_TRACK="1", HYPERFRAMES_TELEMETRY="0")
    npx = "npx.cmd" if os.name == "nt" else "npx"
    subprocess.run([npx, "--no-install", "hyperframes", "telemetry", "disable"], cwd=str(ROOT), env=env, capture_output=True)
    cmd = [npx, "--no-install", "hyperframes", "render", project_dir, "-o", out_mp4, "--fps", str(fps), "--crf", "18", "--workers", "auto"]
    print("  rendering frames with HyperFrames", HF_VERSION)
    r = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_mp4):
        raise RuntimeError("HyperFrames render failed: " + (r.stderr or r.stdout)[-800:])
    tail = [l for l in (r.stdout or "").splitlines() if "rendered" in l.lower() or "frames" in l.lower()]
    if tail:
        print("  " + tail[-1].strip()[:160])


ROOT_DIV = ('<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-fps="{fps}" '
            'data-width="{w}" data-height="{h}" style="position:relative;width:{w}px;height:{h}px;overflow:hidden">')


def toon_project(work, tl_json, size, fps=30):
    """2d engine -> a HyperFrames project folder (index.html + lib/gsap.min.js). No network: League Gothic (bundled)
    stands in for Bebas Neue, Inter is bundled."""
    os.makedirs(os.path.join(work, "lib"), exist_ok=True)
    shutil.copy(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", os.path.join(work, "lib", "gsap.min.js"))
    src = open(ROOT / "toon" / "toon.html", encoding="utf-8").read()
    js = src[src.index("<script>\n") + len("<script>\n"): src.rindex("</script>")]
    js = js.replace("""const F = '"Bebas Neue", Impact, sans-serif'""", """const F = '"League Gothic", "Bebas Neue", Impact, sans-serif'""")
    js = js.replace('await document.fonts.load(`100px "Bebas Neue"`);', 'await document.fonts.load(`100px "League Gothic"`);')
    W, H = size; dur = tl_json["total"]
    html = ("<!doctype html><html><head><meta charset=\"utf-8\"><script src=\"lib/gsap.min.js\"></script>"
            "<style>html,body{margin:0;background:#000}canvas{display:block}</style></head><body>"
            + ROOT_DIV.format(dur=dur, fps=fps, w=W, h=H) + f'<canvas id="c" width="{W}" height="{H}"></canvas></div>'
            "<script>window.__TL = " + json.dumps(tl_json).replace("</", "<\\/") + ";</script><script>\n" + js + "\n"
            "window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};\n"
            "window.__hf.buildReady.toon = window.init(window.__TL).then(() => window.render(0));\n"
            "window.addEventListener('hf-seek', e => { window.render(e.detail.time); });\n"
            "</script></body></html>")
    open(os.path.join(work, "index.html"), "w", encoding="utf-8").write(html)
    return work


def stick_project(web, total, fps=30):
    """stick engine web folder -> also a HyperFrames project: wrap its canvas in the root composition and draw
    frames from the 'hf-seek' time with the engine's own renderFrame()."""
    p = os.path.join(web, "index.html"); html = open(p, encoding="utf-8").read()
    html = html.replace('<canvas id="c"></canvas>', ROOT_DIV.format(dur=total, fps=fps, w=1080, h=1920) + '<canvas id="c"></canvas></div>')
    html = html.replace('<script src="main.js"></script>',
                        '<script src="main.js"></script><script>\n'
                        'window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};\n'
                        'window.__hf.buildReady.stick = Promise.all([document.fonts.load("700 40px Poppins"), document.fonts.load("700 40px Lora")]).then(() => renderFrame(0));\n'
                        'window.addEventListener("hf-seek", e => renderFrame(Math.min(TOTAL_FRAMES - 1, Math.round(e.detail.time * FPS))));\n'
                        '</script>')
    open(p, "w", encoding="utf-8").write(html)
    return web
