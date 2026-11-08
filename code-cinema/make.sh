#!/usr/bin/env bash
# One-shot: ./make.sh projects/<name> [out.mp4]   (script.json -> voice -> timeline -> frames -> audio -> mp4)
set -e; cd "$(dirname "$0")"; P="$1"; OUT="${2:-$P/final.mp4}"
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
python3 tools/tts.py "$P"
python3 tools/build.py "$P"
python3 tools/sfx.py "$P"
node engine/render.js "$P"
python3 tools/mix.py "$P" "$OUT"
