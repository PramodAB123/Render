"""Stock mode: free Pexels / Pixabay vertical clips per line, cut to the voice, captions burned in."""
import json, os, subprocess
import requests
from common import load_config, FFMPEG, WORK, IS_WIN

CACHE = WORK / "clip_cache"
CREDITS = {}   # clip id -> "creator (site) url"; USED_CREDITS goes into the YouTube description
USED_CREDITS = []


def _pexels(q, key):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "orientation": "portrait", "per_page": 12, "size": "medium"}, timeout=30)
    r.raise_for_status(); res = []
    for v in r.json().get("videos", []):
        files = [f for f in v["video_files"] if f.get("height") and f["height"] >= 1280 and f["height"] > f["width"]]
        if files:
            f = min(files, key=lambda f: abs(f["height"] - 1920))
            res.append((f"pexels{v['id']}", f["link"], v["duration"]))
            CREDITS[f"pexels{v['id']}"] = f"{v.get('user', {}).get('name', 'Pexels')} (Pexels) {v.get('url', '')}"
    return res


def _pixabay(q, key):
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 12, "safesearch": "true"}, timeout=30)
    r.raise_for_status(); res = []
    for h in r.json().get("hits", []):
        for size in ("large", "medium"):
            f = h["videos"].get(size) or {}
            if f.get("url"):
                res.append((f"pixabay{h['id']}", f["url"], h["duration"]))
                CREDITS[f"pixabay{h['id']}"] = f"{h.get('user', 'Pixabay')} (Pixabay) {h.get('pageURL', '')}"; break
    return res


def find_clip(query, used, need):
    keys = {"pexels": os.environ.get("PEXELS_API_KEY"), "pixabay": os.environ.get("PIXABAY_API_KEY")}
    for q in (query, " ".join(query.split()[:1]) or query):
        for name, fn in (("pexels", _pexels), ("pixabay", _pixabay)):
            if not keys[name]:
                continue
            try:
                for cid, url, dur in fn(q, keys[name]):
                    if cid not in used:
                        used.add(cid); USED_CREDITS.append(CREDITS.get(cid, cid)); CACHE.mkdir(parents=True, exist_ok=True); p = CACHE / f"{cid}.mp4"
                        if not p.exists():
                            with requests.get(url, stream=True, timeout=120) as r:
                                r.raise_for_status()
                                with open(p, "wb") as fh:
                                    for b in r.iter_content(1 << 20): fh.write(b)
                        return p
            except Exception as e:
                print(f"  {name} search failed for {q!r}: {e}")
    return None


def render(tl, d):
    v = load_config()["video"]; W, H = v["size"]; fps = v["fps"]; S = tl["segs"]; used = set(); parts = []
    for i, s in enumerate(S):
        a = 0 if i == 0 else S[i]["start"]; b = S[i + 1]["start"] if i + 1 < len(S) else tl["total"]; ln = round(b - a, 3)
        clip = find_clip(s.get("visual") or s["text"], used, ln)
        part = os.path.join(d, f"part{i}.mp4"); parts.append(part)
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1,"
              f"eq=brightness=-0.04:saturation=0.85,vignette=PI/5,format=yuv420p")
        if clip:
            print(f"  clip {i}: {clip.name}  ({s.get('visual')})")
            src = ["-stream_loop", "-1", "-i", str(clip)]
        else:
            print(f"  clip {i}: no stock key/result - using a dark placeholder")
            src = ["-f", "lavfi", "-i", f"color=c=0x0d1117:s={W}x{H}:r={fps}"]; vf = "noise=alls=12:allf=t," + vf
        subprocess.run([FFMPEG, "-v", "error", "-y", *src, "-t", str(ln), "-vf", vf, "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", part], check=True)
    with open(os.path.join(d, "parts.txt"), "w") as f:
        f.writelines(f"file 'part{i}.mp4'\n" for i in range(len(parts)))
    # burn captions; run inside d so the ass filter gets a plain relative path on Windows
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt",
                    "-vf", "ass=captions.ass" + (":fontsdir=C\\\\:/Windows/Fonts" if IS_WIN else ""), "-c:v", "libx264", "-crf", "19",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "video.mp4"], check=True, cwd=d)
