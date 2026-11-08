"""Insert shots made with claude-animation-skills "quick skills" (MIT, Artem Novitckii).
/breakdown: a 3D phone that comes apart layer by layer with six labels (three.js). A script line with
shot "breakdown" gets this clip as a full-screen cutaway, cut to the line's length.
The skill's template is filled with our spec and rendered by toon/hf_render.js (no HyperFrames needed)."""
import json, os, shutil, subprocess
from common import ROOT, FFMPEG

SK = ROOT / "vendor" / "animation-skills"
NM = ROOT / "node_modules"


def _link(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)


def prepare(template, spec, dur, work):
    """Same as kit/anim.py prepare(): fill __SPEC__/__DURATION__, copy fonts, GSAP and three.js next to the page."""
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    html = open(template, encoding="utf-8").read()
    data = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    open(os.path.join(work, "index.html"), "w", encoding="utf-8").write(html.replace("__SPEC__", data).replace("__DURATION__", f"{dur:.3f}"))
    for f in (SK / "kit" / "fonts").glob("*.woff2"):
        _link(f, os.path.join(work, "fonts", f.name))
    _link(NM / "gsap" / "dist" / "gsap.min.js", os.path.join(work, "vendor", "gsap.min.js"))
    _link(NM / "three" / "build" / "three.module.js", os.path.join(work, "vendor", "three", "three.module.js"))
    _link(NM / "three" / "examples" / "jsm" / "environments" / "RoomEnvironment.js", os.path.join(work, "vendor", "three", "addons", "environments", "RoomEnvironment.js"))


def breakdown_clip(spec, secs, out, accent):
    labels = [list(map(str, x))[:2] if isinstance(x, (list, tuple)) else [str(x), ""] for x in (spec.get("labels") or [])][:6]
    labels += [["", ""]] * (6 - len(labels))
    s = {"title": str(spec.get("title") or "Phone")[:18], "subtitle": str(spec.get("subtitle") or "Exploded view")[:22], "labels": labels,
         "time": str(spec.get("time") or "9:41")[:5], "date": str(spec.get("date") or "")[:24], "accent": accent}
    work = out + ".work"; dur = max(4.2, secs)
    prepare(SK / "skills" / "breakdown" / "template.html", s, dur, work)
    env = dict(os.environ, NODE_PATH=str(NM))
    subprocess.run(["node", str(ROOT / "toon" / "hf_render.js"), work, out, f"{dur:.3f}"], check=True, env=env)
    shutil.rmtree(work, ignore_errors=True)
    return out


def apply(tl, d, g, size):
    """Overlay every breakdown shot onto d/video.mp4 (full screen, during its line). Never fails the run."""
    segs = [(i, s) for i, s in enumerate(tl["segs"]) if s.get("shot") == "breakdown" or s.get("setup") == "breakdown"]
    if not segs:
        return
    if not (SK / "skills" / "breakdown" / "template.html").exists():
        print("  breakdown shots skipped: vendor/animation-skills is missing"); return
    W, H = size; video = os.path.join(d, "video.mp4"); accent = g.get("thumb_color", "#F08A5D")
    if not accent.startswith("#") or len(accent) != 7:
        accent = "#F08A5D"
    for i, s in segs:
        a = 0 if i == 0 else s["start"]; b = tl["segs"][i + 1]["start"] if i + 1 < len(tl["segs"]) else tl["total"]
        try:
            clip = breakdown_clip(s.get("data") or {}, b - a, os.path.join(d, f"breakdown{i}.mp4"), accent)
            fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b0c0e" if W > H
                   else f"scale={W}:{H}")
            tmp = os.path.join(d, "video_bd.mp4")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-i", video, "-itsoffset", f"{a:.3f}", "-i", clip, "-filter_complex",
                            f"[1:v]{fit},setpts=PTS[bd];[0:v][bd]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})':eof_action=pass[v]",
                            "-map", "[v]", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", tmp], check=True)
            os.replace(tmp, video); print(f"  breakdown shot at {a:.1f}-{b:.1f}s")
        except Exception as e:
            print(f"  breakdown shot {i} skipped ({type(e).__name__}: {str(e)[:120]})")
