#!/usr/bin/env bash
# Fresh container setup (once). Needs network for pip/npm/GitHub. Chromium + Playwright are preinstalled in Claude cloud sessions.
set -e; cd "$(dirname "$0")"
pip install -q kokoro-onnx soundfile numpy
D="${KOKORO_DIR:-/home/claude}"; mkdir -p "$D"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do [ -f "$D/$f" ] || curl -sSL -o "$D/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"; done
fc-list | grep -q "Inter" || (apt-get install -y -q fonts-inter >/dev/null 2>&1 || echo "WARN: install the Inter font")
fc-list | grep -q "JetBrains" || (apt-get install -y -q fonts-jetbrains-mono >/dev/null 2>&1 || true)
echo "ready. three.js is vendored in engine/lib (r169)."
