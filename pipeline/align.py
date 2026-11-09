"""Word timings for a voice clip with NVIDIA Parakeet through sherpa-onnx, the way the stick-figure skill's
tools/align.py does it (free, offline; model in models/sherpa-onnx-nemo-parakeet*). English only.
words(wav, text) -> [{"w","s","e"}] in seconds, spelled as in the script, or None if the model is missing."""
import difflib, glob, re
import numpy as np, soundfile as sf
from common import MODELS

_rec = None


def available():
    return bool(glob.glob(str(MODELS / "sherpa-onnx-nemo-parakeet*" / "encoder.int8.onnx")))


def _recognizer():
    global _rec
    if _rec is None:
        import sherpa_onnx
        d = glob.glob(str(MODELS / "sherpa-onnx-nemo-parakeet*"))[0]
        _rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f"{d}/encoder.int8.onnx", decoder=f"{d}/decoder.int8.onnx",
                                                             joiner=f"{d}/joiner.int8.onnx", tokens=f"{d}/tokens.txt", model_type="nemo_transducer")
    return _rec


def words(wav, text):
    if not available():
        return None
    a, sr = sf.read(wav, dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    dur = len(a) / sr
    if sr != 16000:
        n = int(len(a) * 16000 / sr); a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32); sr = 16000
    rec = _recognizer(); s = rec.create_stream(); s.accept_waveform(sr, a); rec.decode_stream(s); r = s.result
    asr = []
    for tok, ts in zip(r.tokens, r.timestamps):
        if tok.startswith(" ") or tok.startswith("▁") or not asr:
            asr.append([tok.strip(" ▁"), ts])
        else:
            asr[-1][0] += tok
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
    script = text.split(); A = [norm(w[0]) for w in asr]; S = [norm(w) for w in script]
    start = [None] * len(script)
    for blk in difflib.SequenceMatcher(a=S, b=A, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            start[blk.a + k] = asr[blk.b + k][1]
    for i in range(len(script)):   # words the recogniser missed: interpolate between neighbours (as the skill does)
        if start[i] is None:
            lo = next((j for j in range(i - 1, -1, -1) if start[j] is not None), None)
            hi = next((j for j in range(i + 1, len(script)) if start[j] is not None), None)
            t0 = start[lo] if lo is not None else 0.0; t1 = start[hi] if hi is not None else dur
            n0 = lo if lo is not None else -1; n1 = hi if hi is not None else len(script)
            start[i] = t0 + (t1 - t0) * (i - n0) / max(1, n1 - n0)
    out = []
    for i, w in enumerate(script):
        e = start[i + 1] if i + 1 < len(script) else dur
        out.append({"w": w, "s": round(float(start[i]), 3), "e": round(float(max(start[i] + .05, e - .02)), 3)})
    return out
