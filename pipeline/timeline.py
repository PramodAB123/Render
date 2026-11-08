"""Shared timing + captions + music/mix steps used by both render modes."""
import json, os, random, subprocess
from common import load_config, CINEMA, MUSIC, FFMPEG, py

LEAD, GAP, TAIL = 0.25, 0.12, 1.4


def build_timeline(lines, durs, d, extra_cfg=None):
    t = LEAD; segs = []
    for ln, du in zip(lines, durs):
        segs.append({**{k: v for k, v in ln.items() if k != "say"}, "text": ln["say"],
                     "start": round(t, 3), "dur": du})
        t += du + GAP
    total = round(segs[-1]["start"] + segs[-1]["dur"] + TAIL, 2)
    tl = {"cfg": extra_cfg or {}, "segs": segs, "total": total, "music": {"bpm": 84, "gain": 1.0}}
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)
    return tl


def _ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(tl, path):
    v = load_config()["video"]; W, H = v["size"]; hlc = v.get("highlight", "&H004AE3FF")
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,{v['caption_font']},{v['caption_size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for s in tl["segs"]:
        if s.get("nocap"):
            continue
        words = s["text"].split(); hl = str(s.get("hl", "")).lower().strip(".,!?")
        chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
        weights = [sum(len(w) + 2 for w in c) for c in chunks]; t = s["start"]
        for c, wgt in zip(chunks, weights):
            d = s["dur"] * wgt / sum(weights)
            txt = " ".join((f"{{\\c{hlc}}}{w}{{\\c&H00FFFFFF&}}" if hl and w.lower().strip(".,!?\"'") == hl else w) for w in c)
            pop = "{\\fscx70\\fscy70\\t(0,90,\\fscx108\\fscy108)\\t(90,160,\\fscx100\\fscy100)}"
            out.append(f"Dialogue: 0,{_ts(t)},{_ts(t + d)},Cap,,0,0,0,,{pop}{txt.upper()}")
            t += d
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")


def music_and_mix(d, out_mp4):
    """Synth lofi bed + SFX from code-cinema, or a free track from Render\\music, then duck + mix."""
    py(CINEMA / "tools" / "sfx.py", d)
    tracks = [f for f in os.listdir(MUSIC) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))] if MUSIC.exists() else []
    if tracks:
        tl = json.load(open(os.path.join(d, "timeline.json"))); g = load_config()["video"].get("music_gain", 0.9)
        pick = random.choice(tracks); print("  music:", pick)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-stream_loop", "-1", "-i", str(MUSIC / pick), "-t", str(tl["total"] + 1),
                        "-af", f"volume={g * 0.5},afade=t=out:st={tl['total'] - 1.2}:d=1.2", "-ar", "44100", "-ac", "2",
                        os.path.join(d, "music.wav")], check=True)
    else:
        print("  music: synthesized lofi bed (drop free tracks into Render\\music to use your own)")
    py(CINEMA / "tools" / "mix.py", d, out_mp4)
