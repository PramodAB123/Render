# usage: sfx.py <projectDir>   timeline.json -> music.wav (lofi bed, synthesized) + sfx.wav (whooshes, typing, ticks, chimes, hits)
import json, sys, numpy as np, soundfile as sf
h = sys.argv[1]; tl = json.load(open(f'{h}/timeline.json')); T = tl['total']; S = tl['segs']; MU = tl.get('music', {})
SR = 44100; N = int(SR * (T + 1)); rng = np.random.default_rng(7)
def tt(d): return np.arange(int(d * SR)) / SR
def add(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    n = min(len(sig), len(buf) - i); buf[i:i + n] += sig[:n] * g
def lp(x, a):  # one-pole lowpass, a in (0,1): smaller = darker
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s += a * (x[i] - s); y[i] = s
    return y
def lpf(x, k): return np.convolve(x, np.ones(k) / k, 'same')
# ---------------- music: lofi chords (Rhodes-ish), bass, soft drums, vinyl crackle
bpm = MU.get('bpm', 84); beat = 60 / bpm; bar = beat * 4
prog = MU.get('chords', [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]])  # Fmaj7 Em7 Dm7 Cmaj7
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
mus = np.zeros(N)
def ep(f, d):
    x = tt(d); e = np.exp(-x * 2.2) * (1 - np.exp(-x * 200))
    return (np.sin(2 * np.pi * f * x) + .3 * np.sin(2 * np.pi * 2 * f * x) * np.exp(-x * 5) + .08 * np.sin(2 * np.pi * 3 * f * x) * np.exp(-x * 8)) * e
b = 0; t = 0.0
while t < T + bar:
    ch = prog[b % len(prog)]
    for hit, g in ((0, 1), (beat * 2.5, .55)):
        for j, m in enumerate(ch): add(mus, ep(hz(m), bar), t + hit + j * .012, .09 * g)
    x = tt(bar); add(mus, np.sin(2 * np.pi * hz(ch[0] - 12) * x) * np.exp(-x * 1.2) * (1 - np.exp(-x * 80)), t, .22)
    for k in range(4):
        bt = t + k * beat
        if k in (0, 2): x = tt(.35); add(mus, np.sin(2 * np.pi * (50 + 60 * np.exp(-x * 30)) * x) * np.exp(-x * 9), bt, .5)
        if k in (1, 3): add(mus, lpf(rng.uniform(-1, 1, int(.18 * SR)), 6) * np.exp(-tt(.18) * 22), bt, .16)
        for o in (0, .5): add(mus, (rng.uniform(-1, 1, int(.04 * SR))) * np.exp(-tt(.04) * 90), bt + o * beat + (.03 if o else 0), .03)
    t += bar; b += 1
crackle = (rng.uniform(0, 1, N) > .9993) * rng.uniform(-.5, .5, N) + lpf(rng.normal(0, .004, N), 30)
mus = lp(mus, .35) + crackle * .5
# duck the bed during "flat" (bad-version) segments: thin + quiet, then hit back on the next golden seg
gain = np.ones(N); prev = None
for i, s in enumerate(S):
    look = s.get('look', prev or 'golden')
    a = int(s['start'] * SR); e = int((S[i + 1]['start'] if i + 1 < len(S) else T + 1) * SR)
    if look == 'flat': gain[a:e] = .25
    prev = look
gain = lpf(gain, 2000); mus *= gain * MU.get('gain', 1.0)
fo = int(1.2 * SR); mus[-fo - SR:-SR] *= np.linspace(1, 0, fo); mus[-SR:] = 0; mus[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
# ---------------- sfx
fx = np.zeros(N)
def whoosh(t, g=.35):
    n = int(.5 * SR); w = lpf(rng.uniform(-1, 1, n), 10) * np.sin(np.linspace(0, np.pi, n)) ** 3; add(fx, w, t - .3, g)
def click(t, g=.25):
    x = tt(.03); add(fx, (np.sin(2 * np.pi * 3200 * x) * .4 + rng.uniform(-1, 1, len(x))) * np.exp(-x * 260), t, g)
def tick(t, f=1500, g=.18): x = tt(.25); add(fx, np.sin(2 * np.pi * f * x) * np.exp(-x * 18), t, g)
def chime(t, g=.22):
    for j, f in enumerate((784, 988, 1175, 1568)): x = tt(.9); add(fx, np.sin(2 * np.pi * f * x) * np.exp(-x * 4), t + j * .07, g)
def boom(t, g=.8): x = tt(1.4); add(fx, np.sin(2 * np.pi * (38 + 40 * np.exp(-x * 6)) * x) * np.exp(-x * 2.5), t, g)
def swipe(t, g=.25): n = int(.25 * SR); add(fx, lpf(rng.uniform(-1, 1, n), 3) * np.linspace(1, 0, n) ** 2, t, g)
def riser(t, d=.8, g=.12):
    x = tt(d); n = lpf(rng.uniform(-1, 1, len(x)), 4) * (x / d) ** 2; add(fx, n, t - d, g)
prev = None
for i, s in enumerate(S):
    st = s['start']
    if i and s.get('shot') not in ('same', prev): whoosh(st)
    if s.get('shot') != 'same': prev = s.get('shot')
    sc = s.get('screen') or {}
    if sc.get('type') == 'title' and sc.get('strike'): boom(st, .7); swipe(st + sc.get('strikeAt', .5))
    for w in s.get('strike', []): swipe(st + .4)
    if sc.get('type') == 'app' and sc.get('typed'):
        cps = sc.get('cps', 16); t0 = st + sc.get('typeAt', .25)
        for c in range(len(sc['typed'])): click(t0 + c / cps + rng.uniform(-.01, .01), .18 + rng.uniform(0, .08))
        if sc.get('click'): click(t0 + len(sc['typed']) / cps + .25, .45)
    if sc.get('type') == 'xp':
        nxt = S[i + 1]['start'] if i + 1 < len(S) else T; d = nxt - st; items = sc.get('checks', ['camera', 'light', 'motion', 'sound'])
        for j in range(len(items)): tick(st + (j + 1) * d * .8 / (len(items) + .5), 1200 + j * 200)
    if sc.get('type') == 'levelup': chime(st)
    if s.get('cta'): riser(st, .8); boom(st, .6); chime(st + .1, .15)
    if s.get('look') == 'golden' and i and S[i - 1].get('look') == 'flat': boom(st, .5)
sf.write(f'{h}/music.wav', np.clip(mus, -1, 1).astype(np.float32), SR)
sf.write(f'{h}/sfx.wav', np.clip(fx, -1, 1).astype(np.float32), SR)
print('music+sfx ok')
