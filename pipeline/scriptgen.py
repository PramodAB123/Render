"""Step 2: write the script with a free local LLM (Ollama) in the genre's style. Falls back to a genre template."""
import json, os
import requests
from common import load_config

PROMPT = """You write viral 25-35 second vertical YouTube Shorts. Genre: {genre}. Niche: {niche}.
Style: {tone}
Write ONE completely original video (never copy an existing video or story).
Starting idea: {idea}
{inspo}
Rules: line 1 is a scroll-stopping hook under 10 words. 7 to 10 lines total, each 4-14 words.
The last line ends with exactly: "{cta}"
For every line give a 2-3 word stock-footage search ("visual") that matches the genre: {visual_hint}.
Reply with JSON only, exactly this shape:
{{"title": "under 70 chars, curiosity title", "description": "2 sentences", "tags": ["5-10 tags"],
  "thumb_text": "2-4 WORDS", "lines": [{{"say": "...", "visual": "2-3 words", "hl": "one key word from say"}}]}}"""

FALLBACK = {
    "horror": ["You have ten seconds to decide.", "{idea}.", "Everything goes quiet. Too quiet.",
               "Then you hear it again. Closer.", "Your phone has one bar of battery left.",
               "Do you hide, or do you run?"],
    "comedy": ["Nobody talks about this, but everyone does it.", "{idea}.", "Step one: act completely normal.",
               "Step two: panic, but quietly.", "Step three: blame the dog.", "And somehow it still works every time."],
    "science": ["Here is something your brain will not believe.", "{idea}.", "Scientists have studied this for decades.",
                "The answer is stranger than you think.", "It changes how you see everything around you.",
                "And it is happening right now."],
    "motivation": ["Listen. This is for you.", "{idea}.", "Every day you wait, the gap gets bigger.",
                   "Nobody sees the work you do in the dark.", "But one day, everyone sees the results.",
                   "Start today. Not Monday. Today."],
    "mystery": ["This has never been explained.", "{idea}.", "Witnesses reportedly saw nothing unusual.",
                "But one detail does not add up.", "Investigators reportedly closed the case without answers.",
                "So what really happened?"],
}


def from_ollama(g, idea, inspo):
    cfg = load_config()["llm"]
    ins = ("Trending titles right now (for tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
    r = requests.post(f'{cfg["host"]}/api/generate', json={
        "model": os.environ.get("LLM_MODEL", cfg["model"]),
        "prompt": PROMPT.format(genre=g["name"], niche=g["niche"], tone=g["tone"], idea=idea, inspo=ins,
                                cta=g["cta"], visual_hint=g["visual_hint"]),
        "format": "json", "stream": False, "options": {"temperature": 0.9}}, timeout=600)
    r.raise_for_status()
    data = json.loads(r.json()["response"])
    lines = [l for l in data.get("lines", []) if isinstance(l, dict) and l.get("say")]
    if len(lines) < 4:
        raise ValueError("LLM returned too few lines")
    data["lines"] = lines
    return data


def fallback(g, idea):
    if "(for example: " in idea:
        idea = idea.split("(for example: ", 1)[1].rstrip(")")
    text = [t.format(idea=idea.rstrip(".")) for t in FALLBACK.get(g["name"], FALLBACK["horror"])] + [g["cta"]]
    words = g["visual_hint"].split('"')
    examples = [words[i] for i in range(1, len(words), 2)] or [g["visual_style"]]
    lines = [{"say": t, "visual": examples[i % len(examples)], "hl": max(t.split(), key=len).strip(".,?!")}
             for i, t in enumerate(text)]
    return {"title": idea[:70], "description": idea, "tags": [], "thumb_text": " ".join(idea.split()[:3]).upper(), "lines": lines}


def write_script(g, idea, inspo, use_llm=True):
    if use_llm:
        try:
            s = from_ollama(g, idea, inspo); print("  script written by Ollama:", s["title"]); return s
        except Exception as e:
            print("  Ollama not available or failed (", e, ") - using the built-in template")
    return fallback(g, idea)
