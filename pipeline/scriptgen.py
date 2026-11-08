"""Step 2: write the script with a free local LLM (Ollama). Falls back to a simple template."""
import json, re
import requests
from common import load_config

PROMPT = """You write viral 25-35 second vertical short videos for the niche: {niche}.
Write ONE completely original story (do not copy any existing video).
Idea to start from: {idea}
{inspo}
Rules: first line is a scroll-stopping hook under 10 words. 7 to 10 lines total, each 4-14 words,
present tense, second person ("you"), rising tension, last line is a cliffhanger plus "Follow for part two."
For every line give 2-3 simple English stock-footage search words that show that moment (e.g. "dark hallway").
Reply with JSON only, exactly this shape:
{{"title": "under 70 chars, curiosity title", "description": "2 sentences", "tags": ["5-10 tags"],
  "thumb_text": "2-4 WORDS", "lines": [{{"say": "...", "visual": "dark hallway", "hl": "one key word from say"}}]}}"""


def from_ollama(idea, inspo):
    cfg = load_config()["llm"]; niche = load_config()["niche"]
    ins = ("Titles trending right now (for tone only):\n- " + "\n- ".join(inspo)) if inspo else ""
    import os
    r = requests.post(f'{cfg["host"]}/api/generate', json={
        "model": os.environ.get("LLM_MODEL", cfg["model"]), "prompt": PROMPT.format(niche=niche, idea=idea, inspo=ins),
        "format": "json", "stream": False, "options": {"temperature": 0.9}}, timeout=600)
    r.raise_for_status()
    data = json.loads(r.json()["response"])
    lines = [l for l in data.get("lines", []) if isinstance(l, dict) and l.get("say")]
    if len(lines) < 4:
        raise ValueError("LLM returned too few lines")
    data["lines"] = lines
    return data


def fallback(idea):
    words = re.findall(r"[A-Za-z']+", idea)
    key = max(words, key=len) if words else "night"
    lines = [
        {"say": "You have ten seconds to decide.", "visual": "clock ticking dark", "hl": "ten"},
        {"say": idea.rstrip(".") + ".", "visual": "dark house night", "hl": key},
        {"say": "Everything is quiet. Too quiet.", "visual": "empty hallway night", "hl": "quiet."},
        {"say": "Then you hear it again.", "visual": "door creaking", "hl": "again."},
        {"say": "Your phone has one bar of battery left.", "visual": "phone low battery", "hl": "battery"},
        {"say": "Do you hide, or do you run?", "visual": "running in the dark", "hl": "run?"},
        {"say": "Comment what you would do. Follow for part two.", "visual": "flashlight forest night", "hl": "Follow"},
    ]
    return {"title": f"Would you survive this? {idea[:40]}", "description": idea, "tags": [],
            "thumb_text": "WOULD YOU RUN?", "lines": lines}


def write_script(idea, inspo, use_llm=True):
    if use_llm:
        try:
            s = from_ollama(idea, inspo); print("  script written by Ollama:", s["title"]); return s
        except Exception as e:
            print("  Ollama not available or failed (", e, ") - using the built-in template")
    return fallback(idea)
