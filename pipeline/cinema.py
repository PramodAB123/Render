"""Cinema mode: the code-cinema three.js room (every frame rendered in code, no stock footage)."""
import json, os, subprocess
from common import CINEMA, ROOT, py

SHOTS = ["low_hero", "wide_window", "orbit_wide", "keyboard_slide", "mug_phone", "screen_full", "top_down", "pull_back"]


def to_cinema_script(sc, fast=True):
    lines = sc["lines"]; segs = []
    hook = (sc.get("thumb_text") or "WAIT").split()[0].upper()[:10]
    for i, ln in enumerate(lines):
        s = {"say": ln["say"], "hl": [ln["hl"]] if ln.get("hl") else []}
        if i == 0:
            s.update(shot="screen_push", look="golden", screen={"type": "title", "text": hook, "sub": sc.get("title", "")[:40]})
        elif i == len(lines) - 1:
            s.update(shot="cta", cta="FOLLOW", nocap=True, ctaTop="", ctaBottom="for part two", minDur=2.6, screen={"type": "off"})
        else:
            s["shot"] = SHOTS[(i - 1) % len(SHOTS)]
            if i == 1:
                s["screen"] = {"type": "app", "title": "night_one.story", "typed": sc.get("title", "")[:28], "cps": 18}
        segs.append(s)
    cfg = {"size": [1080, 1920], "fps": 30, "captionPos": "top", "note": "PART\nONE"}
    if fast:
        cfg["glScale"] = 0.66
    return {"cfg": cfg, "music": {"bpm": 84, "gain": 1.0}, "segs": segs}


def render(sc, d, fast=True, preview=False):
    """Voice files s*.wav must already be in d. Writes d/video.mp4 (or preview jpgs)."""
    json.dump(to_cinema_script(sc, fast), open(os.path.join(d, "script.json"), "w"), indent=1)
    py(CINEMA / "tools" / "build.py", d)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"))
    args = ["node", str(CINEMA / "engine" / "render.js"), d] + (["preview", "1", "6", "12"] if preview else [])
    subprocess.run(args, check=True, env=env)
