"""Topic -> a full scene-by-scene screenplay sized to the chosen length (free local LLM, Ollama).
The screenplay uses the same format people paste into the script box (Scene / Visual steps / Camera / Music / SFX /
Narrator), so every mode then builds its pictures, objects, motion, camera and music from it."""
import json, os, re, requests
from common import load_config

STYLE = {
    "zdf": ("a 3D cartoon 'what if' explainer in the Zack D. Films format: an 'If you...' hook, 'some people think...', a 'But' twist, "
            "examples that build, the real mechanism, and a payoff that answers the hook. Check the facts. People, props and clear physical "
            "actions (shooting, swinging, hitting, falling, pointing) in every Visual step, so they can be animated."),
    "cinema": "a cinematic 3D animated short. Every Visual step names the place, the people or animals, the objects and what they do.",
    "stick": "an animated stick-figure story with a clear hook, rising tension, a twist and a punchline ending.",
    "ai": "an illustrated animated story with vivid places, a clear hook, rising tension, a twist and a strong ending.",
}
PROMPT = """Write the screenplay for {style}
Topic: {topic}
Theme / tone: {tone}
Length: {secs} seconds of narration = about {words} spoken words in total, in {scenes} scenes.
{inspo}
Rules:
- NOT a film script: no headings like "EXT.", "INT.", "CUT TO", "DAY", "FADE IN". Visual steps are plain sentences describing what we SEE.
- Every Visual step has a PERSON (say who: a knight in plate armour, a blacksmith, a scientist in a lab coat, two soldiers ...),
  what they WEAR or HOLD, and a physical ACTION with an OBJECT (swings a sword at, shoots a bullet at, hammers steel on an anvil,
  points at a screen showing "TEXT", holds up a vest ...). Show the idea, don't just name a place.
- Good step: "A soldier fires a pistol at a man in a steel vest; the bullet flattens against the plate in slow motion."
  Bad step: "EXT. BATTLEFIELD - DAY" or "Ancient warriors" or "Blacksmiths forge steel plates" (who exactly, holding what, doing what to what?).
- Each scene has ONE narrator line (or one or two short character lines) of about {per} words. Spoken words only in "say".
- Each scene has 3 to 5 Visual steps: short, concrete, filmable sentences naming WHO, WHAT objects and WHAT happens.
  Put any words that appear on screens, signs or documents in double quotes inside the step.
- "camera" says the shots: wide, medium, close-up, extreme close-up, low angle, tracking, side view, aerial, zoom in, zoom out, orbit.
- "music" is the feel (tense, playful, epic, mysterious, sad, horror, action) and "sfx" the sounds.
- No stage directions in "say". No emojis. Same language as the topic.
Reply JSON only:
{{"title": "under 60 chars", "scenes": [{{"title": "...", "visual": ["...", "..."], "camera": ["..."], "music": "...", "sfx": "...",
  "speaker": "Narrator", "say": "..."}}]}}"""


def _ollama(prompt, n=3000):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt, "format": "json",
                      "stream": False, "options": {"temperature": .8, "num_ctx": 6144, "num_predict": n}}, timeout=1800)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def to_text(j):
    """JSON screenplay -> the script-box format the screenplay reader understands."""
    out = []
    for i, s in enumerate(j.get("scenes", []), 1):
        vis = []
        for v in (s.get("visual") or []):   # drop film-script headings the model sometimes writes anyway
            v = re.sub(r"^\s*(?:CUT TO|FADE (?:IN|OUT|TO)|DISSOLVE TO)\s*[:\-–—]*\s*", "", str(v).strip(), flags=re.I)
            v = re.sub(r"^\s*(?:EXT|INT)\.?\s*", "", v, flags=re.I)
            v = re.sub(r"\s*[-–—]\s*(?:DAY|NIGHT|DAWN|DUSK|MORNING|EVENING|CONTINUOUS)\s*$", "", v, flags=re.I).strip(" -–—.")
            if v and not (v.isupper() and len(v.split()) <= 6):   # a bare ALL-CAPS heading says nothing to animate
                vis.append(v[0].upper() + v[1:] + ("" if v.endswith((".", "!", "?", '"')) else "."))
            elif v:
                vis.append("Show " + v.lower() + ".")
        say = re.sub(r"\s+", " ", str(s.get("say") or "")).replace('"', "'").strip()
        if not say:
            continue
        cam = s.get("camera") or []
        cam = [cam] if isinstance(cam, str) else cam
        spk = str(s.get("speaker") or "Narrator").strip() or "Narrator"
        out.append(f"Scene {i} – {str(s.get('title') or f'Scene {i}').strip()}")
        out.append("Visual:\n" + "\n".join(f"- {v}" for v in vis))
        if cam:
            out.append("Camera:\n" + "\n".join(f"- {c}" for c in cam))
        if s.get("music"):
            out.append(f"Music: {s['music']}")
        if s.get("sfx"):
            out.append(f"SFX: {s['sfx']}")
        out.append(f'{"Narrator" if spk.lower() == "narrator" else spk}: "{say}"')
        out.append("")
    return "\n".join(out)


def write(topic, secs, mode, g, inspo=()):
    """-> screenplay text (or None if the LLM isn't available)."""
    words = int(secs * 2.5); scenes = max(3, min(24, round(secs / 7))); per = max(8, round(words / scenes))
    p = PROMPT.format(style=STYLE.get(mode, STYLE["cinema"]), topic=topic, tone=g.get("tone", ""), secs=secs, words=words, scenes=scenes, per=per,
                      inspo=("Inspiration (do not copy): " + "; ".join(inspo)) if inspo else "")
    for attempt in range(3):
        try:
            j = _ollama(p, n=min(8000, 600 + scenes * 260))
            text = to_text(j)
            spoken = sum(len(m.split()) for m in re.findall(r':\s*"([^"]+)"', text))
            steps = len(re.findall(r"^- ", text, re.M)); nsc = max(1, len(j.get("scenes", [])))
            if attempt < 2 and steps < nsc * 2.5:
                p += f"\nYour last answer had only {steps} Visual steps for {nsc} scenes. Give EVERY scene 3 to 5 Visual steps with a person doing something to an object."
                continue
            if spoken < words * .55 and attempt < 2:   # too short for the length: ask again, firmer
                p += f"\nYour last answer had only {spoken} spoken words. Write {scenes} scenes with about {per} spoken words EACH."
                continue
            print(f"  screenplay written from the topic: {len(j.get('scenes', []))} scenes, {spoken} spoken words for {secs}s", flush=True)
            return text
        except Exception as e:
            print(f"  screenwriter retry ({type(e).__name__}: {str(e)[:80]})", flush=True)
    return None
