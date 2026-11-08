# usage: tts.py <projectDir>   script.json -> s0.wav, s1.wav ... (one per seg, Kokoro TTS)
# seg "voice" overrides the script voice for one line. Models: KOKORO_DIR (default /home/claude)
import json, os, sys, subprocess, soundfile as sf
from kokoro_onnx import Kokoro
D = os.environ.get('KOKORO_DIR', '/home/claude')
k = Kokoro(f'{D}/kokoro-v1.0.onnx', f'{D}/voices-v1.0.bin')
h = sys.argv[1]; sc = json.load(open(f'{h}/script.json'))
FX = sc.get('voiceFx', 'highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,equalizer=f=3000:t=q:w=1:g=2,volume=1.4')
for i, sg in enumerate(sc['segs']):
    v = sg.get('voice', sc.get('voice', 'am_michael')); sp = sg.get('speed', sc.get('speed', 1.0))
    a, sr = k.create(sg['say'], voice=v, speed=sp, lang='en-gb' if v[0] == 'b' else 'en-us')
    sf.write(f'{h}/raw{i}.wav', a, sr)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{h}/raw{i}.wav', '-af', FX + ',silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse', '-ac', '1', '-ar', '44100', f'{h}/s{i}.wav'], check=True)
    print(i, round(sf.info(f'{h}/s{i}.wav').duration, 2), sg['say'])
