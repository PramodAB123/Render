"""Shared paths, config and helpers for the free video pipeline."""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
CINEMA = ROOT / "code-cinema"
WORK = ROOT / "work"
OUTPUT = ROOT / "output"
SECRETS = ROOT / "secrets"
MUSIC = ROOT / "music"
MODELS = ROOT / "models"

# Put our bundled ffmpeg first on PATH so every tool (and code-cinema) finds it.
os.environ["PATH"] = str(BIN) + os.pathsep + os.environ.get("PATH", "")
FFMPEG = str(BIN / "ffmpeg.exe") if (BIN / "ffmpeg.exe").exists() else "ffmpeg"
IS_WIN = os.name == "nt"
os.environ.setdefault("FFMPEG", FFMPEG)
os.environ.setdefault("KOKORO_DIR", str(MODELS))


def load_env():
    """Read KEY=value lines from Render/.env into os.environ (never overwrites real env vars)."""
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def slug(text, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n].strip("-") or "video"


def ff(*args):
    """Run ffmpeg quietly; raise on failure."""
    subprocess.run([FFMPEG, "-v", "error", "-y", *map(str, args)], check=True)


def py(script, *args):
    """Run a Python tool (e.g. one of code-cinema/tools) with this interpreter."""
    subprocess.run([sys.executable, str(script), *map(str, args)], check=True)


load_env()
