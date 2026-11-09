"""Step 3: voice every line -> <dir>/s0.wav, s1.wav ... in the genre's voice, plus exact word timings.
Engines: edge (free online Microsoft voices, gives word timings), kokoro or piper (offline, timings estimated).
Each line gets ln["words"] = [{"w", "s", "e"}] in seconds from the start of its clip, so captions can follow
the voice word by word (the approach of the stick-figure skill in claude-animation-skills)."""
import asyncio, glob, os, re, shutil, subprocess, time
import soundfile as sf
from common import load_config, ff, MODELS

BASE_FX = "highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,equalizer=f=3000:t=q:w=1:g=2,volume=1.4"
TAIL_TRIM = "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
HEAD_TRIM = "silenceremove=start_periods=1:start_threshold=-45dB"
SAFE_VOICE = "en-US-GuyNeural"


async def _edge_stream(text, out, voice, rate, pitch):
    import edge_tts
    words = []
    with open(out, "wb") as f:
        async for ch in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary").stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":   # offsets are in 100-nanosecond units
                s = ch["offset"] / 1e7; words.append({"w": ch["text"], "s": round(s, 3), "e": round(s + ch["duration"] / 1e7, 3)})
    return words


def _edge(text, out, voice, rate, pitch):
    v = voice
    for attempt in range(9):  # the free Edge voice service drops connections now and then: keep retrying, waiting longer
        try:
            return asyncio.run(_edge_stream(text, out, v, rate, pitch))
        except Exception as e:
            if attempt == 8:
                raise
            if "NoAudio" in type(e).__name__ and attempt >= 2:   # the voice itself is not available: use one that always exists
                v = SAFE_VOICE
            print(f"  edge-tts retry {attempt + 1} ({type(e).__name__})"); time.sleep(min(2 ** attempt, 30))


_kokoro = None
def _kokoro_say(text, out, voice, speed):
    global _kokoro
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        _kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    a, sr = _kokoro.create(text, voice=voice, speed=speed, lang="en-gb" if voice[0] == "b" else "en-us")
    sf.write(out, a, sr)


def _piper(text, out):
    model = (glob.glob(str(MODELS / "piper" / "*.onnx")) or [None])[0]
    exe = shutil.which("piper")
    if not (exe and model):
        raise RuntimeError("piper.exe on PATH and a voice .onnx in models\\piper are needed")
    subprocess.run([exe, "-m", model, "-f", out], input=text.encode(), check=True)


def estimate_words(text, dur):
    """No timings from the engine: spread the words over the clip by their length."""
    ws = text.split(); tot = sum(len(w) + 1 for w in ws) or 1; t = 0.0; out = []
    for w in ws:
        d = dur * (len(w) + 1) / tot; out.append({"w": w, "s": round(t, 3), "e": round(t + d * 0.9, 3)}); t += d
    return out


def voice_lines(lines, d, g):
    v = load_config()["voice"]; gv = g.get("voice", {}); eng = v.get("engine", "edge")
    os.makedirs(d, exist_ok=True); durs = []
    for i, ln in enumerate(lines):
        e = ln.get("engine") or eng   # a line may ask for its own engine (stick mode: the skill's Kokoro narrator)
        if e == "kokoro" and not (MODELS / "kokoro-v1.0.onnx").exists():
            e = "edge"
        raw = os.path.join(d, f"raw{i}" + (".mp3" if e == "edge" else ".wav")); words = None
        if e == "kokoro":
            try:
                _kokoro_say(ln["say"], raw, ln.get("kvoice") or gv.get("kokoro_voice", v["kokoro_voice"]), float(ln.get("kspeed") or v.get("speed", 1.0)))
                import align
                words = align.words(raw, ln["say"])   # Parakeet word timings, as the skill's align.py
            except Exception as ex:
                print(f"  kokoro failed on line {i} ({type(ex).__name__}); using the Edge voice"); e = "edge"
                raw = os.path.join(d, f"raw{i}.mp3"); words = None
        if e == "kokoro":
            pass
        elif e == "piper":
            _piper(ln["say"], raw)
        else:
            # a line can carry its own voice / rate / pitch (2D mode: each character speaks with its own voice)
            words = _edge(ln["say"], raw, ln.get("voice") or gv.get("edge_voice", SAFE_VOICE), ln.get("rate") or gv.get("rate", "+0%"),
                          ln.get("pitch") or gv.get("pitch", "+0Hz"))
        out = os.path.join(d, f"s{i}.wav")
        if words:   # cut the lead-in silence exactly where the first word starts, so word times stay exact
            lead = max(0.0, words[0]["s"] - 0.04)
            fx = ",".join(x for x in (f"atrim=start={lead:.3f},asetpts=PTS-STARTPTS", BASE_FX, gv.get("fx", ""), TAIL_TRIM) if x)
            words = [{"w": w["w"], "s": round(w["s"] - lead, 3), "e": round(w["e"] - lead, 3)} for w in words]
        else:
            fx = ",".join(x for x in (HEAD_TRIM, BASE_FX, gv.get("fx", ""), TAIL_TRIM) if x)
        ff("-i", raw, "-af", fx, "-ac", 1, "-ar", 44100, out)
        dur = round(sf.info(out).duration, 3); durs.append(dur)
        ln["words"] = [w for w in (words or estimate_words(ln["say"], dur)) if w["s"] < dur]
        print(f"  voice {i}: {dur:.2f}s  {ln['say']}")
    return durs


def fit_length(lines, durs, d, target, gap):
    """Bring the narration close to the length that was asked for.
    Too long: speed every line up together (max 1.25x, pitch kept). Too short: longer pauses (max +0.6 s per line).
    Returns (durs, gap)."""
    eff = lambda: sum(max(du, float(ln.get('minDur') or 0)) for du, ln in zip(durs, lines))   # cutaways keep their minimum length
    total = eff() + gap * len(durs) + 1.7
    if target and total > target * 1.06:
        f = min(1.25, total / target)
        for i, ln in enumerate(lines):
            p = os.path.join(d, f"s{i}.wav"); tmp = os.path.join(d, f"s{i}.tmp.wav")
            ff("-i", p, "-af", f"atempo={f:.4f}", tmp); os.replace(tmp, p)
            durs[i] = round(sf.info(p).duration, 3)
            ln["words"] = [{"w": w["w"], "s": round(w["s"] / f, 3), "e": round(w["e"] / f, 3)} for w in ln.get("words", [])]
        print(f"  length: {total:.0f}s narrated for a {target}s video -> voice sped up {f:.2f}x")
    elif target and total < target * 0.94:
        extra = min(0.6, (target - total) / max(1, len(durs)))
        gap += extra; print(f"  length: {total:.0f}s narrated for a {target}s video -> pauses +{extra:.2f}s per line")
    new = eff() + gap * len(durs) + 1.7
    print(f"  length: final about {new:.0f}s" + (f" (asked {target}s)" if target else " (your script's own length)"))
    return durs, gap
