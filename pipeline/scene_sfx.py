"""Scene sound design, made in code (free): every scene gets its own ambience and hits, added to sfx.wav
under the voice. Used by stick and 2d. Like the reference Shorts: a whoosh on each cut, fire crackle and hammer
clinks in the forge, drums and a crowd roar for armies, a horn for kingdoms, wind and a heartbeat at night."""
import os
import numpy as np, soundfile as sf

SR = 44100
rng = np.random.default_rng(11)


def _t(d): return np.arange(int(d * SR)) / SR
def _smooth(x, k): c = np.cumsum(np.concatenate([np.zeros(k), x])); return (c[k:] - c[:-k]) / k
def _noise(d, k=1): return _smooth(rng.uniform(-1, 1, int(d * SR) + k), k)[:int(d * SR)]
def _env(n, a=.01, r=.3): t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / r)


def whoosh(): n = int(.6 * SR); return _noise(.6, 12) * np.sin(np.linspace(0, np.pi, n)) ** 3 * .5
def boom(): x = _t(1.3); return np.sin(2 * np.pi * (40 + 45 * np.exp(-x * 7)) * x) * np.exp(-x * 2.6) + _noise(1.3, 30) * np.exp(-x * 5) * .5
def clink(): x = _t(.5); return sum(np.sin(2 * np.pi * f * x) * np.exp(-x * 9) for f in (1800, 2650, 4100)) * .35
def thump(): x = _t(.25); return np.sin(2 * np.pi * (55 + 30 * np.exp(-x * 30)) * x) * np.exp(-x * 14)
def chime(): x = _t(1.2); return sum(np.sin(2 * np.pi * f * x) * np.exp(-x * 3.5) for f in (988, 1319, 1568, 1976)) * .2
def pop(): x = _t(.18); return np.sin(2 * np.pi * (500 + 900 * np.exp(-x * 40)) * x) * np.exp(-x * 25) * .6
def step(): x = _t(.12); return _noise(.12, 4) * np.exp(-x * 45) * .5
def horn():
    x = _t(1.6); f = np.where(x < .55, 196, 262); ph = np.cumsum(2 * np.pi * f / SR)
    return (2 * ((ph / (2 * np.pi)) % 1) - 1) * np.minimum(1, x / .08) * np.exp(-np.maximum(0, x - 1.1) * 6) * .18


def ambience(kind, d):
    if kind == "fire":
        crack = (rng.uniform(0, 1, int(d * SR)) > .9985) * rng.uniform(-1, 1, int(d * SR)); return _smooth(crack, 3) * 3 + _noise(d, 60) * .25
    if kind == "wind": return _noise(d, 200) * (0.6 + 0.4 * np.sin(_t(d) * 0.8)) * 2.2
    if kind == "water": return _noise(d, 25) * .35
    if kind == "crowd": x = _t(d); return _noise(d, 40) * np.minimum(1, x / 1.5) * .9
    return np.zeros(int(d * SR))


SCENES = {   # setup/shot -> (ambience, gain, hits)
    "forge": ("fire", .5, "clink"), "armies": ("crowd", .6, "drums"), "kingdoms": ("wind", .25, "horn"), "night": ("wind", .45, "heart"),
    "bridge": ("water", .4, None), "sea": ("water", .45, None), "impact": (None, 0, "boom"), "reveal": (None, 0, "chime"),
    "blueprint": (None, 0, "stamp"), "messenger": ("wind", .2, "run"), "run": (None, 0, "run"), "walk": (None, 0, "walk"),
    "bigtext": (None, 0, "pop"), "throne": ("fire", .15, None), "black": ("wind", .3, None), "map": (None, 0, None),
}


def add(d, tl, gain=0.38):
    p = os.path.join(d, "sfx.wav"); fx, sr = sf.read(p, dtype="float32")
    if fx.ndim > 1:
        fx = fx.mean(axis=1)
    N = len(fx)

    def put(sig, t, g):
        i = int(t * SR); n = min(len(sig), N - i)
        if 0 <= i < N and n > 0:
            fx[i:i + n] += (sig[:n] * g).astype(np.float32)
    segs = tl["segs"]; prev = None
    for k, s in enumerate(segs):
        kind = s.get("setup") or s.get("shot") or "char"; a = 0 if k == 0 else s["start"]
        b = segs[k + 1]["start"] if k + 1 < len(segs) else tl["total"]; d_ = max(.1, b - a)
        if k and kind != prev:
            put(whoosh(), a - .3, gain * .9)
        prev = kind
        amb, ag, hit = SCENES.get(kind, (None, 0, None))
        if amb:
            sig = ambience(amb, d_); fade = np.minimum(1, np.minimum(np.arange(len(sig)), len(sig) - np.arange(len(sig))) / (.25 * SR)); put(sig * fade, a, gain * ag)
        if hit == "boom": put(boom(), a + .05, gain * 1.6)
        elif hit == "chime": put(chime(), a + .7, gain)
        elif hit == "pop": put(pop(), a + .05, gain)
        elif hit == "horn": put(horn(), a + .2, gain)
        elif hit == "stamp": put(thump(), a + .95, gain * 1.4)
        elif hit == "clink":
            for t in np.arange(a + .25, b, 2 * np.pi / 6): put(clink(), t, gain * .9)
        elif hit == "drums":
            for j, t in enumerate(np.arange(a, b, .5)): put(thump(), t, gain * (1.2 if j % 2 == 0 else .8))
        elif hit == "heart":
            for t in np.arange(a + .2, b, .85): put(thump(), t, gain * .9); put(thump(), t + .22, gain * .6)
        elif hit in ("run", "walk"):
            for t in np.arange(a, b, .21 if hit == "run" else .35): put(step(), t, gain * .7)
    sf.write(p, np.clip(fx, -1, 1), SR)
