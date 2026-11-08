# usage: build.py <projectDir>   script.json + s*.wav durations -> timeline.json (what the engine renders)
import json, sys, soundfile as sf
h = sys.argv[1]; sc = json.load(open(f'{h}/script.json')); cfg = sc.get('cfg', {})
t = cfg.get('lead', .25); segs = []
for i, s in enumerate(sc['segs']):
    d = round(sf.info(f'{h}/s{i}.wav').duration, 3)
    o = {k: v for k, v in s.items() if k not in ('say',)}; o['text'] = s.get('text', s['say']); o['start'] = round(t, 3); o['dur'] = max(d, s.get('minDur', 0))
    segs.append(o); t += o['dur'] + s.get('gap', cfg.get('gap', .12))
total = round(segs[-1]['start'] + segs[-1]['dur'] + cfg.get('tail', 1.4), 2)
json.dump({'cfg': cfg, 'segs': segs, 'total': total, 'music': sc.get('music', {})}, open(f'{h}/timeline.json', 'w'), indent=1)
print('total', total, 's')
