"""Step 3: voice every line -> <dir>/s0.wav, s1.wav ... in the genre's voice.
Engines: edge (free online Microsoft voices), kokoro or piper (offline)."""
import asyncio, glob, os, shutil, subprocess, time
import soundfile as sf
from common import load_config, ff, MODELS

BASE_FX = "highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,equalizer=f=3000:t=q:w=1:g=2,volume=1.4"
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB,areverse")
SAFE_VOICE = "en-US-GuyNeural"


def _edge(text, out, voice, rate, pitch):
    import edge_tts
    for attempt in range(6):  # the free Edge voice service drops connections now and then
        v = voice if attempt < 4 else SAFE_VOICE  # last tries: a voice that always exists
        try:
            return asyncio.run(edge_tts.Communicate(text, v, rate=rate, pitch=pitch).save(out))
        except Exception as e:
            if attempt == 5:
                raise
            print(f"  edge-tts retry {attempt + 1} ({type(e).__name__})"); time.sleep(min(2 ** attempt, 10))


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


def voice_lines(lines, d, g):
    v = load_config()["voice"]; gv = g.get("voice", {}); eng = v.get("engine", "edge")
    fx = ",".join(x for x in (BASE_FX, gv.get("fx", ""), TRIM) if x)
    os.makedirs(d, exist_ok=True); durs = []
    for i, ln in enumerate(lines):
        raw = os.path.join(d, f"raw{i}" + (".mp3" if eng == "edge" else ".wav"))
        if eng == "kokoro":
            _kokoro_say(ln["say"], raw, gv.get("kokoro_voice", v["kokoro_voice"]), v.get("speed", 1.0))
        elif eng == "piper":
            _piper(ln["say"], raw)
        else:
            _edge(ln["say"], raw, gv.get("edge_voice", SAFE_VOICE), gv.get("rate", "+0%"), gv.get("pitch", "+0Hz"))
        out = os.path.join(d, f"s{i}.wav")
        ff("-i", raw, "-af", fx, "-ac", 1, "-ar", 44100, out)
        durs.append(round(sf.info(out).duration, 3))
        print(f"  voice {i}: {durs[-1]:.2f}s  {ln['say']}")
    return durs
