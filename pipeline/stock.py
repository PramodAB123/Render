"""Visuals for each line: free Pexels/Pixabay clips, free AI images (with Ken Burns motion), or a mix.
Every scene is cut to its voice line, colour-graded for the genre, then captions are burned in."""
import os, subprocess, time
import requests
from common import load_config, FFMPEG, WORK, IS_WIN

CACHE = WORK / "clip_cache"
CREDITS = {}   # clip id -> "creator (site) url"; USED_CREDITS goes into the YouTube description
USED_CREDITS = []
_last_call = [0.0]


def _polite():
    """Pixabay allows 100 requests/minute; stay well under it on long videos."""
    wait = 0.8 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


def _pexels(q, key, portrait):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "orientation": "portrait" if portrait else "landscape", "per_page": 12}, timeout=30)
    r.raise_for_status(); res = []
    for v in r.json().get("videos", []):
        files = [f for f in v["video_files"] if f.get("height") and min(f["height"], f["width"]) >= 720
                 and (f["height"] > f["width"]) == portrait]
        if files:
            f = min(files, key=lambda f: abs(max(f["height"], f["width"]) - 1920))
            res.append((f"pexels{v['id']}", f["link"]))
            CREDITS[f"pexels{v['id']}"] = f"{v.get('user', {}).get('name', 'Pexels')} (Pexels) {v.get('url', '')}"
    return res


def _pixabay(q, key, portrait):
    _polite()
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 20, "safesearch": "true"}, timeout=30)
    r.raise_for_status(); res = []
    for h in r.json().get("hits", []):
        for size in ("large", "medium"):
            f = h["videos"].get(size) or {}
            if f.get("url"):
                tall = (f.get("height") or 0) > (f.get("width") or 1)
                res.append((tall == portrait, f"pixabay{h['id']}", f["url"]))
                CREDITS[f"pixabay{h['id']}"] = f"{h.get('user', 'Pixabay')} (Pixabay) {h.get('pageURL', '')}"; break
    res.sort(key=lambda x: not x[0])  # matching orientation first; others get cropped
    return [(cid, url) for _, cid, url in res]


def find_clip(query, used, style="", portrait=True):
    keys = {"pexels": os.environ.get("PEXELS_API_KEY"), "pixabay": os.environ.get("PIXABAY_API_KEY")}
    tries = [f"{query} {style}".strip(), query, query.split()[0] if query.split() else query, style or query]
    for q in dict.fromkeys(t for t in tries if t):
        for name, fn in (("pexels", _pexels), ("pixabay", _pixabay)):
            if not keys[name]:
                continue
            try:
                for cid, url in fn(q, keys[name], portrait):
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


def _ken_burns(i, W, H, fps, n):
    """Slow zoom/pan on a still image; direction changes every scene."""
    z = ["1+0.14*on/{n}", "1.14-0.14*on/{n}", "1.12", "1.12"][i % 4].format(n=n)
    x = ["iw/2-iw/zoom/2", "iw/2-iw/zoom/2", "(iw-iw/zoom)*on/{n}", "(iw-iw/zoom)*(1-on/{n})"][i % 4].format(n=n)
    return (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
            f"zoompan=z='{z}':x='{x}':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps={fps}")


def _plan(S, visuals, ic):
    """Which scenes get an AI image. doc: chapter openings + every other scene, stock clips in between."""
    if visuals == "ai":
        want = [True] * len(S); cap = ic.get("max_images", 24)
    elif visuals == "mix":
        want = [i % 2 == 0 for i in range(len(S))]; cap = ic.get("max_images_mix", 10)
    elif visuals == "doc":
        want = [bool(s.get("chapter")) or i % 2 == 1 for i, s in enumerate(S)]; cap = ic.get("max_images_doc", 12)
    else:
        return [False] * len(S)
    out, n = [], 0
    for w in want:
        out.append(w and n < cap); n += 1 if (w and n < cap) else 0
    return out


def render(tl, d, g, size, visuals="stock"):
    """visuals: stock | ai | mix | doc. Writes d/video.mp4 with captions.
    doc = documentary look: AI stills with slow camera moves + stock footage, crossfades, cinematic bars."""
    W, H = size; portrait = H > W; fps = load_config()["video"]["fps"]; S = tl["segs"]; used = set(); parts = []
    ic = load_config()["image"]; plan = _plan(S, visuals, ic); planned = sum(plan); ai_count = 0
    doc = visuals == "doc"; T = load_config()["video"].get("crossfade", 0.8) if doc else 0; Tf = int(round(T * fps))
    base = []
    for i, s in enumerate(S):
        a = 0 if i == 0 else S[i]["start"]; b = S[i + 1]["start"] if i + 1 < len(S) else tl["total"]; ln = round(b - a, 3)
        nb = max(1, int(round(ln * fps))); base.append(nb)
        n = nb + (Tf if i + 1 < len(S) else 0)          # extra frames overlap with the next scene's crossfade
        part = os.path.join(d, f"part{i}.mp4"); parts.append(part)
        grade = f"{g.get('grade', 'null')},format=yuv420p"; src = None; vf = None
        if plan[i]:
            img = os.path.join(d, f"img{i}.png")
            try:
                import imagegen
                t0 = time.time()
                imagegen.generate(s.get("image") or s.get("visual") or s["text"], img, portrait,
                                  g.get("image_style", "") + (", documentary film still" if doc else ""), seed=i)
                ai_count += 1; dt = time.time() - t0
                print(f"  scene {i + 1}/{len(S)}: AI image {ai_count}/{planned} in {dt:.0f}s  ({(s.get('image') or s.get('visual') or '')[:60]})")
                if ai_count == 1 and planned > 1:
                    print(f"  (about {dt * (planned - 1) / 60:.0f} more minutes for the remaining AI images)")
                src = ["-i", img]; vf = _ken_burns(i, W, H, fps, n) + ",setsar=1," + grade
            except Exception as e:
                print(f"  scene {i + 1}: AI image failed ({type(e).__name__}: {str(e)[:100]}) - using stock footage")
        if src is None:
            clip = find_clip(s.get("visual") or s["text"], used, g.get("visual_style", ""), portrait)
            if clip:
                print(f"  scene {i + 1}/{len(S)}: clip {clip.name}  ({s.get('visual')})")
                src = ["-stream_loop", "-1", "-i", str(clip)]
                slow = "setpts=1.25*PTS," if doc else ""   # documentary: slightly slowed, calmer footage
                vf = f"{slow}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1," + grade
            else:
                print(f"  scene {i + 1}: no stock key/result - dark placeholder")
                src = ["-f", "lavfi", "-i", f"color=c=0x0d1117:s={W}x{H}:r={fps}"]; vf = "noise=alls=12:allf=t," + grade
        subprocess.run([FFMPEG, "-v", "error", "-y", *src, "-frames:v", str(n), "-vf", vf, "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(fps), part], check=True)
    subs = "ass=captions.ass" + (":fontsdir=C\\\\:/Windows/Fonts" if IS_WIN else "")
    if doc and len(parts) > 1:
        # crossfade every cut; dip through black at each new chapter
        inputs = []; fl = []; prev = "[0:v]"; off = 0.0
        for p in parts:
            inputs += ["-i", os.path.basename(p)]
        for k in range(1, len(parts)):
            off += base[k - 1] / fps
            tr = "fadeblack" if S[k].get("chapter") else "fade"
            fl.append(f"{prev}[{k}:v]xfade=transition={tr}:duration={T}:offset={off:.3f}[x{k}]"); prev = f"[x{k}]"
        bars = ",drawbox=x=0:y=0:w=iw:h=ih*0.1:color=black:t=fill,drawbox=x=0:y=ih*0.9:w=iw:h=ih*0.1:color=black:t=fill" if not portrait else ""
        fl.append(f"{prev}format=yuv420p{bars},{subs}[v]")
        subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fl), "-map", "[v]",
                        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "video.mp4"], check=True, cwd=d)
        return
    with open(os.path.join(d, "parts.txt"), "w") as f:
        f.writelines(f"file 'part{i}.mp4'\n" for i in range(len(parts)))
    # burn captions; run inside d so the ass filter gets a plain relative path on Windows
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt",
                    "-vf", subs, "-c:v", "libx264", "-crf", "20",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "video.mp4"], check=True, cwd=d)
