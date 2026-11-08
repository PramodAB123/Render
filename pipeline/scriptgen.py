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


# ---------------- long-form (1-10 minute, 16:9) ----------------
OUTLINE = """You plan a {minutes}-minute narrated YouTube video. Genre: {genre}. Niche: {niche}.
Style: {tone}
Write ONE completely original story/topic (never copy an existing video). Starting idea: {idea}
{inspo}
Split it into exactly {chapters} chapters that build to a strong ending.
Reply with JSON only:
{{"title": "under 70 chars, curiosity title", "description": "3 sentences", "tags": ["8-12 tags"],
  "thumb_text": "2-4 WORDS", "chapters": [{{"heading": "...", "summary": "2 sentences of what happens"}}]}}"""

CHAPTER = """You are writing the narration of a {minutes}-minute {genre} YouTube video titled "{title}".
Style: {tone}
Full plan: {plan}
Now write chapter {n} of {total}: "{heading}" - {summary}
{prev}
Write about {words} words of narration as {lines} lines, each line 10-22 words, spoken naturally.
{extra}
For every line also give:
 "visual": a 2-3 word stock-footage search ({visual_hint}),
 "image": a vivid one-sentence description of the scene for an AI image generator (subject, setting, lighting, camera angle; no text, no words),
 "hl": one key word from the line.
Reply with JSON only: {{"lines": [{{"say": "...", "visual": "...", "image": "...", "hl": "..."}}]}}"""

WPM = 150  # narration speed


def _ollama(prompt, num_predict=2048):
    cfg = load_config()["llm"]
    r = requests.post(f'{cfg["host"]}/api/generate', json={
        "model": os.environ.get("LLM_MODEL", cfg["model"]), "prompt": prompt, "format": "json", "stream": False,
        "options": {"temperature": 0.85, "num_ctx": 8192, "num_predict": num_predict}}, timeout=1200)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def write_long(g, idea, inspo, minutes, use_llm=True):
    chapters = max(3, min(16, round(minutes * 1.6)))
    words_total = minutes * WPM; words = max(60, words_total // chapters); lines_per = max(4, round(words / 16))
    if use_llm:
        try:
            ins = ("Trending titles (tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
            plan = _ollama(OUTLINE.format(minutes=minutes, genre=g["name"], niche=g["niche"], tone=g["tone"], idea=idea,
                                          inspo=ins, chapters=chapters), 1500)
            chs = [c for c in plan.get("chapters", []) if isinstance(c, dict) and c.get("heading")][:chapters]
            if len(chs) < 2:
                raise ValueError("outline too short")
            print(f"  outline: {plan.get('title')!r}, {len(chs)} chapters")
            plan_txt = " | ".join(f"{i + 1}. {c['heading']}: {c.get('summary', '')}" for i, c in enumerate(chs))
            lines = []
            for n, c in enumerate(chs, 1):
                extra = ("Start with a gripping hook line." if n == 1 else "") + \
                        (f' The final line must end with exactly: "{g["cta"]}"' if n == len(chs) else "")
                prev = ("The previous chapter ended with: " + " ".join(l["say"] for l in lines[-3:])) if lines else ""
                for attempt in range(2):
                    try:
                        part = _ollama(CHAPTER.format(minutes=minutes, genre=g["name"], title=plan.get("title", idea),
                                                      tone=g["tone"], plan=plan_txt, n=n, total=len(chs), heading=c["heading"],
                                                      summary=c.get("summary", ""), prev=prev, words=words, lines=lines_per,
                                                      extra=extra, visual_hint=g["visual_hint"]))
                        new = [l for l in part.get("lines", []) if isinstance(l, dict) and l.get("say")]
                        if new:
                            lines += new; break
                    except Exception as e:
                        print(f"  chapter {n} retry ({e})")
                print(f"  chapter {n}/{len(chs)}: {c['heading']}  (total {sum(len(l['say'].split()) for l in lines)} words)")
            if sum(len(l["say"].split()) for l in lines) < words_total * 0.4:
                raise ValueError("script came out too short")
            plan["lines"] = lines
            return plan
        except Exception as e:
            raise SystemExit(f"Long videos need the Ollama script writer, and it failed ({e}). "
                             "Nothing was uploaded. Please run the workflow again.")
    raise SystemExit("Long videos need the Ollama script writer (remove --no-llm).")


def write_script(g, idea, inspo, use_llm=True):
    if use_llm:
        try:
            s = from_ollama(g, idea, inspo); print("  script written by Ollama:", s["title"]); return s
        except Exception as e:
            print("  Ollama not available or failed (", e, ") - using the built-in template")
    return fallback(g, idea)
