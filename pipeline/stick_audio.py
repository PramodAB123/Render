"""Music and final mix for stick mode, ported from the stick-figure skill's audio.py (claude-animation-skills,
MIT, Artem Novitckii). Same instruments (pizzicato, glockenspiel, reed, strings), same "whimsical comedic underscore"
and "sneak" patterns, the same VO compression, ducking (music x .22, ducked 55% under the voice, SFX x .7) and the
same master (limiter + loudnorm -14 LUFS, 48 kHz). The original places every cue by hand for one reel; here the cues
follow the scenes of our timeline automatically."""
import json, os, subprocess
import numpy as np, soundfile as sf
from scipy import signal
from common import FFMPEG

SR = 44100
rng = np.random.default_rng(3)
TENSE = {"night", "storm", "ghost", "skeletons", "jungle", "temple", "impact", "run"}


def T(n): return np.arange(n) / SR
def bp(x, lo, hi, order=2): b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), .99)], 'band'); return signal.lfilter(b, a, x)
def lp(x, f, order=2): b, a = signal.butter(order, f / (SR / 2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, order=2): b, a = signal.butter(order, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def midi(m): return 440 * 2 ** ((m - 69) / 12)


def pluck(f, dur=.5, bright=.5):   # Karplus-Strong exactly as in the skill (its effective update: average x .995)
    n = int(dur * SR); p = int(SR / f); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = .5 * (buf[i % p] + buf[(i + 1) % p]) * .995
    return out


_cache = {}
def pizz(m, dur=.45, g=1.0):
    k = ('pz', m, round(dur, 2))
    if k not in _cache:
        x = pluck(midi(m), dur); n = len(x); t = T(n)
        x = bp(x, 180, 3500) * np.exp(-t * 7) + bp(rng.standard_normal(n), 1500, 5000) * np.exp(-t * 300) * .15
        _cache[k] = x / (np.max(np.abs(x)) + 1e-9)
    return _cache[k] * g
def glock(m, dur=1.2, g=1.0):
    n = int(dur * SR); t = T(n); f = midi(m)
    x = (np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6) + .15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12))
    return x * np.exp(-t * 3.5) * np.minimum(1, t / .002) * .5 * g
def reed(m, dur=.22, g=1.0):
    n = int(dur * SR); t = T(n); f = midi(m); ph = (f * t) % 1
    x = lp(np.sign(np.sin(2 * np.pi * ph)) * .6 + (2 * ph - 1) * .4, 900)
    return x * np.minimum(1, t / .015) * np.exp(-t * 6) * np.minimum(1, (dur - t) / .03) * .5 * g
def strings(ms, dur, g=1.0):
    n = int(dur * SR); t = T(n); x = np.zeros(n)
    for m in ms:
        for d in (-.004, 0, .005):
            ph = np.cumsum(midi(m) * (1 + d) * (1 + .003 * np.sin(2 * np.pi * 5 * t))) / SR; x += 2 * (ph % 1) - 1
    x = lp(x / (len(ms) * 3), 1100); e = np.minimum(1, t / .5) * np.minimum(1, (dur - t) / .5)
    return x * e * g


DM = [(38, (62, 65, 69)), (43, (62, 67, 71)), (38, (62, 65, 69)), (45, (61, 64, 67))]   # Dm G Dm A7
DMAJ = [(38, (62, 66, 69)), (43, (62, 67, 71)), (45, (61, 64, 69)), (38, (62, 66, 69))]  # D G A D
MOTIF = [(0, 74), (.5, 77), (1, 81), (2, 79), (2.5, 77), (3, 76)]


def score(segs, total, genre):
    """The skill's underscore, placed per scene: playful pizzicato for light scenes, the reed 'sneak' for tense ones,
    string swells on impacts/reveals, a glockenspiel sparkle on reveals and the hook."""
    N = int((total + 1) * SR); music = np.zeros(N); BEAT = 60 / 104
    def place(x, at, g=1.0):
        i = int(at * SR); j = min(N, i + len(x))
        if 0 <= i < N: music[i:j] += x[:j - i] * g
    def playful(t0, t1, prog, g=1.0, glock_on=True):
        t, bar = t0, 0
        while t < t1 - .05:
            root, ch = prog[bar % 4]
            place(pizz(root, .5, .9), t, g); place(pizz(root + 7, .5, .7), t + 2 * BEAT, g)
            for bt in (1, 3):
                for m in ch: place(pizz(m - 12, .3, .28), t + bt * BEAT, g)
            if glock_on and bar % 2 == 0:
                for (bt, m) in MOTIF:
                    if t + bt * BEAT < t1: place(glock(m, 1.0, .35), t + bt * BEAT, g)
            t += 4 * BEAT; bar += 1
    def sneak(t0, t1, g=1.0):
        steps = [38, 38, 41, 40, 39, 38, 36, 37]; t, i = t0, 0
        while t < t1 - .05:
            place(reed(steps[i % 8] + 12, .2, .8), t, g); place(pizz(steps[i % 8], .35, .6), t, g); t += BEAT; i += 1
    dark_genre = genre in ("horror", "mystery")
    k = 0
    while k < len(segs):   # group neighbouring scenes of the same feel into one musical passage
        tense = (segs[k].get("setup") in TENSE) or dark_genre; j = k
        while j + 1 < len(segs) and ((segs[j + 1].get("setup") in TENSE) or dark_genre) == tense:
            j += 1
        t0 = 0 if k == 0 else segs[k]["start"]; t1 = segs[j + 1]["start"] if j + 1 < len(segs) else total
        if tense:
            sneak(t0, t1, .8); place(strings((50, 56, 62), min(4, t1 - t0), .25), t0)
        else:
            playful(t0, t1, DM if (k // 3) % 2 == 0 else DMAJ, .8, glock_on=k > 0)
        k = j + 1
    for (bt, m) in MOTIF:                                   # little sparkle on the hook
        place(glock(m, 1.0, .3), .4 + bt * BEAT * .5)
    for s in segs:
        if s.get("setup") in ("impact", "reveal", "treasuremap", "ghost"):
            place(strings((50, 57, 62, 65), 2.4, .4), s["start"])
        if s.get("setup") in ("reveal", "treasuremap"):
            for i, m in enumerate([62, 65, 69, 72, 74, 77]): place(glock(m, .9, .28 + i * .02), s["start"] + .3 + i * .2)
    end = segs[-1]["start"]                                  # button at the end, as in the skill
    place(strings((50, 57, 62, 66), 1.4, .5), end); [place(pizz(m - 12, .8, .5), end + .05) for m in (62, 66, 69, 74)]
    return lp(music, 6000)


def mix(d, out_mp4, tl, genre):
    """VO + music + SFX exactly like the skill's audio.py mix, then the skill's master (make.sh) with our video encode."""
    total = tl["total"]; N = int((total + 1) * SR)
    vo, vsr = sf.read(os.path.join(d, "voice.wav"))
    if vo.ndim > 1: vo = vo.mean(1)
    vo = signal.resample_poly(vo, SR, vsr) if vsr != SR else vo
    vo = hp(vo, 90)
    envv = lp(np.abs(signal.hilbert(vo)), 20)                                  # gentle compression
    vo = vo * np.where(envv > .15, (.15 / np.maximum(envv, 1e-6)) ** .4, 1.0)
    vo = vo / (np.max(np.abs(vo)) + 1e-9) * .9
    VO = np.zeros(N); VO[:min(N, len(vo))] = vo[:N]
    music = score(tl["segs"], total, genre); music = np.pad(music, (0, max(0, N - len(music))))[:N]
    fx, _ = sf.read(os.path.join(d, "sfx.wav")); fx = fx.mean(1) if fx.ndim > 1 else fx; fx = np.pad(fx, (0, max(0, N - len(fx))))[:N]
    venv = lp(np.abs(VO), 6); duck = 1 - .55 * np.clip(venv / .05, 0, 1)    # duck music under VO
    m = VO * 1.0 + music * .22 * duck + fx * .7
    out = np.stack([m, m], 1); fl = int(.5 * SR); out[-fl:] *= np.linspace(1, 0, fl)[:, None]
    out = out / (np.max(np.abs(out)) + 1e-9) * .89
    sf.write(os.path.join(d, "mix.wav"), out, SR)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", os.path.join(d, "video.mp4"), "-i", os.path.join(d, "mix.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-color_range", "tv",
                    "-af", "alimiter=limit=0.8:attack=2:release=60,loudnorm=I=-14:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", out_mp4], check=True)
    print("  wrote", out_mp4, "(stick-figure skill mix: -14 LUFS)")
