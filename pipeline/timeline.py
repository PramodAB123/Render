"""Shared timing + captions + music/mix steps used by both render modes."""
import json, os, random, subprocess
from common import load_config, CINEMA, MUSIC, FFMPEG, py

LEAD, GAP, TAIL = 0.25, 0.12, 1.4


def build_timeline(lines, durs, d, g, extra_cfg=None, gap=None):
    t = LEAD; segs = []; gap = g.get("gap", GAP) if gap is None else gap
    for ln, du in zip(lines, durs):
        du = max(du, float(ln.get("minDur") or 0))   # a breakdown cutaway needs ~4 s to come apart and show its labels
        seg = {**{k: v for k, v in ln.items() if k not in ("say", "words")}, "text": ln["say"], "start": round(t, 3), "dur": du}
        if ln.get("words"):   # word timings in video seconds (captions follow the voice word by word)
            seg["words"] = [{"w": w["w"], "s": round(t + w["s"], 3), "e": round(t + w["e"], 3)} for w in ln["words"]]
        segs.append(seg)
        t += du + gap
    total = round(segs[-1]["start"] + segs[-1]["dur"] + TAIL, 2)
    tl = {"cfg": extra_cfg or {}, "segs": segs, "total": total, "music": g.get("music", {"bpm": 84, "gain": 1.0})}
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)
    return tl


def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(tl, path, g, size=None):
    """Shorts: big centred 3-word pop captions. Long videos (16:9): subtitle-style lines at the bottom."""
    v = load_config()["video"]; W, H = size or v["size"]; hlc = g.get("highlight", "&H004AE3FF"); long_form = W > H
    fs = v.get("long_caption_size", 60) if long_form else g.get("caption_size", v["caption_size"])
    align, margin, per, outline = (2, 80, 8, 4) if long_form else (5, 0, 3, 7)
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,{v['caption_font']},{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},3,{align},80,80,{margin},1",
           f"Style: Title,{v['caption_font']},{int(fs * 1.5)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,6,0,1,3,0,5,80,80,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for k, s in enumerate(tl["segs"]):
        if long_form and s.get("chapter"):
            out.append(f"Dialogue: 1,{_ts(s['start'])},{_ts(s['start'] + 3.2)},Title,,0,0,0,,{{\\fad(600,600)}}"
                       f"{{\\fs{int(fs * 0.55)}}}CHAPTER {sum(1 for x in tl['segs'][:k + 1] if x.get('chapter'))}\\N{{\\fs{int(fs * 1.5)}}}{s['chapter'].upper()}")
    for s in tl["segs"]:
        if s.get("nocap"):
            continue
        hl = str(s.get("hl", "") if not isinstance(s.get("hl"), list) else (s["hl"] or [""])[0]).lower().strip(".,!?")
        if s.get("words"):   # exact timings from the voice
            ws = s["words"]; groups = [ws[i:i + per] for i in range(0, len(ws), per)]; end = s["start"] + s["dur"]
            timed = [([w["w"] for w in grp], grp[0]["s"], (groups[k + 1][0]["s"] if k + 1 < len(groups) else end)) for k, grp in enumerate(groups)]
        else:
            words = s["text"].split(); chunks = [words[i:i + per] for i in range(0, len(words), per)]
            weights = [sum(len(w) + 2 for w in c) for c in chunks]; t0 = s["start"]; timed = []
            for c, wgt in zip(chunks, weights):
                dd = s["dur"] * wgt / sum(weights); timed.append((c, t0, t0 + dd)); t0 += dd
        for c, t, t_end in timed:
            d = t_end - t
            txt = " ".join((f"{{\\c{hlc}}}{w}{{\\c&H00FFFFFF&}}" if hl and w.lower().strip(".,!?\"'") == hl else w) for w in c)
            pop = "" if long_form else "{\\fscx70\\fscy70\\t(0,90,\\fscx108\\fscy108)\\t(90,160,\\fscx100\\fscy100)}"
            out.append(f"Dialogue: 0,{_ts(t)},{_ts(t + d)},Cap,,0,0,0,,{pop}{txt if long_form else txt.upper()}")
            t += d
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


def _voice_track(d, tl):
    """All voice lines placed at their start times in one file (fast, any number of lines)."""
    import numpy as np, soundfile as sf
    SR = 44100; buf = np.zeros(int((tl["total"] + 1) * SR), dtype=np.float32)
    for i, s in enumerate(tl["segs"]):
        a, sr = sf.read(os.path.join(d, f"s{i}.wav"), dtype="float32")
        if a.ndim > 1:
            a = a.mean(axis=1)
        st = int(s["start"] * SR); n = min(len(a), len(buf) - st)
        if n > 0:
            buf[st:st + n] += a[:n]
    sf.write(os.path.join(d, "voice.wav"), np.clip(buf, -1, 1), SR)


def _doc_sound(d, tl):
    """Documentary sound design: soft whoosh on every cut, low boom on each chapter, quiet room-tone drone."""
    import numpy as np, soundfile as sf
    p = os.path.join(d, "sfx.wav"); fx, SR = sf.read(p, dtype="float32")
    if fx.ndim > 1:
        fx = fx.mean(axis=1)
    rng = np.random.default_rng(3); N = len(fx)
    def put(sig, t, g):
        i = int(t * SR); n = min(len(sig), N - i)
        if 0 <= i < N and n > 0:
            fx[i:i + n] += sig[:n] * g
    def smooth(x, k):
        c = np.cumsum(np.concatenate([np.zeros(k), x])); return (c[k:] - c[:-k]) / k
    for k, s in enumerate(tl["segs"]):
        if k:
            n = int(0.9 * SR); w = smooth(rng.uniform(-1, 1, n + 40), 40)[:n] * np.sin(np.linspace(0, np.pi, n)) ** 2
            put(w, s["start"] - 0.6, 0.18)
        if s.get("chapter"):
            x = np.arange(int(2.5 * SR)) / SR; put(np.sin(2 * np.pi * (36 + 30 * np.exp(-x * 4)) * x) * np.exp(-x * 1.6), s["start"], 0.55)
    drone = smooth(rng.normal(0, 1, N + 400), 400)[:N]; drone *= 0.05 / (np.abs(drone).max() + 1e-9)
    sf.write(p, np.clip(fx + drone, -1, 1), SR)


def music_and_mix(d, out_mp4, g, doc=False):
    """Synth genre music bed + SFX (code-cinema), or a free track from music/<genre>/, then duck under the voice + mix."""
    tl = json.load(open(os.path.join(d, "timeline.json")))
    py(CINEMA / "tools" / "sfx.py", d)
    # free tracks: Render/music/<genre>/ first, then Render/music/
    tracks = []
    for folder in (MUSIC / g["name"], MUSIC):
        if folder.exists():
            tracks = [folder / f for f in os.listdir(folder) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))]
        if tracks:
            break
    if tracks:
        gain = load_config()["video"].get("music_gain", 0.9)
        pick = random.choice(tracks); print("  music:", pick.name)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-stream_loop", "-1", "-i", str(pick), "-t", str(tl["total"] + 1),
                        "-af", f"volume={gain * 0.5},afade=t=out:st={tl['total'] - 1.2}:d=1.2", "-ar", "44100", "-ac", "2",
                        os.path.join(d, "music.wav")], check=True)
    else:
        print(f"  music: synthesized {g['name']} bed (add free tracks to music/{g['name']}/ to use your own)")
    if doc:
        _doc_sound(d, tl)
    _voice_track(d, tl)
    f = (f"[1]aformat=channel_layouts=stereo,asplit[voice][key];"
         f"[2]aformat=channel_layouts=stereo,volume=0.9[mus];[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];"
         f"[3]aformat=channel_layouts=stereo[fx];[voice][duck][fx]amix=inputs=3:normalize=0,alimiter=limit=0.95,atrim=0:{tl['total']}[a]")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", os.path.join(d, "video.mp4"), "-i", os.path.join(d, "voice.wav"),
                    "-i", os.path.join(d, "music.wav"), "-i", os.path.join(d, "sfx.wav"), "-filter_complex", f,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out_mp4], check=True)
    print("  wrote", out_mp4)
