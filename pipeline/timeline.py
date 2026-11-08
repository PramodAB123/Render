"""Shared timing + captions + music/mix steps used by both render modes."""
import json, os, random, subprocess
from common import load_config, CINEMA, MUSIC, FFMPEG, py

LEAD, GAP, TAIL = 0.25, 0.12, 1.4


def build_timeline(lines, durs, d, g, extra_cfg=None):
    t = LEAD; segs = []; gap = g.get("gap", GAP)
    for ln, du in zip(lines, durs):
        segs.append({**{k: v for k, v in ln.items() if k != "say"}, "text": ln["say"],
                     "start": round(t, 3), "dur": du})
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
    align, margin, per, outline = (2, 80, 7, 4) if long_form else (5, 0, 3, 7)
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,{v['caption_font']},{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},3,{align},80,80,{margin},1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for s in tl["segs"]:
        if s.get("nocap"):
            continue
        words = s["text"].split(); hl = str(s.get("hl", "")).lower().strip(".,!?")
        chunks = [words[i:i + per] for i in range(0, len(words), per)]
        weights = [sum(len(w) + 2 for w in c) for c in chunks]; t = s["start"]
        for c, wgt in zip(chunks, weights):
            d = s["dur"] * wgt / sum(weights)
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


def music_and_mix(d, out_mp4, g):
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
    _voice_track(d, tl)
    f = (f"[1]aformat=channel_layouts=stereo,asplit[voice][key];"
         f"[2]aformat=channel_layouts=stereo,volume=0.9[mus];[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];"
         f"[3]aformat=channel_layouts=stereo[fx];[voice][duck][fx]amix=inputs=3:normalize=0,alimiter=limit=0.95,atrim=0:{tl['total']}[a]")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", os.path.join(d, "video.mp4"), "-i", os.path.join(d, "voice.wav"),
                    "-i", os.path.join(d, "music.wav"), "-i", os.path.join(d, "sfx.wav"), "-filter_complex", f,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out_mp4], check=True)
    print("  wrote", out_mp4)
