# usage: mix.py <projectDir> <out.mp4>   voice lines + music (sidechain-ducked under the voice) + sfx -> final mp4
import json, subprocess, sys
h, out = sys.argv[1], sys.argv[2]; tl = json.load(open(f'{h}/timeline.json')); S = tl['segs']; n = len(S)
a = ['ffmpeg', '-v', 'error', '-y']
for i in range(n): a += ['-i', f'{h}/s{i}.wav']
a += ['-i', f'{h}/video.mp4', '-i', f'{h}/music.wav', '-i', f'{h}/sfx.wav']; f = []
for i, s in enumerate(S): ms = int(s['start'] * 1000); f.append(f'[{i}]adelay={ms}|{ms},apad[v{i}]')
f.append(''.join(f'[v{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0:duration=longest,atrim=0:{tl["total"]},aformat=channel_layouts=stereo,asplit[voice][key]')
f.append(f'[{n+1}]aformat=channel_layouts=stereo,volume=0.9[mus];[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck]')
f.append(f'[{n+2}]aformat=channel_layouts=stereo[fx];[voice][duck][fx]amix=inputs=3:normalize=0,alimiter=limit=0.95[a]')
a += ['-filter_complex', ';'.join(f), '-map', f'{n}:v', '-map', '[a]', '-c:v', 'libx264', '-crf', '23', '-maxrate', '10M', '-bufsize', '20M', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-shortest', out]
subprocess.run(a, check=True); print('wrote', out)
