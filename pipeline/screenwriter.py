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
PROMPT = """You write the screenplay for {style}
Topic: {topic}
Theme / tone: {tone}
Length: {secs} seconds = about {words} spoken words in total, in {scenes} scenes (about {per} spoken words per scene).
{inspo}
The video is BUILT from your screenplay: every place becomes a background, every character a model with the clothes you
describe, every object a prop, every Visual step one shot, every Camera line an angle. So be exact and physical.

THE STRUCTURE (each scene, in this order):
  Scene <n> – <short title>
  Place: where it happens, specific and visual ("a Roman test range with straw targets", "a blacksmith's forge at night")
  Time: day | dawn | dusk | night
  Characters: each person or animal on screen, with what they LOOK like ("Marcus: a Roman legionnaire in red tunic, steel helmet and lorica segmentata armour")
  Objects: the props that must be built ("a 9mm pistol", "a breastplate on a wooden stand", "a straw target")
  Visual: 3 to 5 steps, each one shot: WHO does WHAT to WHICH object ("Marcus fires the pistol at the breastplate; the bullet dents the steel in slow motion")
          Words shown on screens, signs or papers go in double quotes inside the step.
  Camera: one angle per step: wide, medium, close-up, extreme close-up, low angle, tracking, side view, aerial, zoom in, zoom out, orbit, over the shoulder
  Music: tense | playful | epic | mysterious | sad | horror | action
  SFX: the sounds
  Narrator: "the spoken line"          (and/or)   Dialogue – <Character name>: "what they say"

Rules:
- Spoken words ONLY in Narrator / Dialogue lines. No stage directions inside them.
- NOT a film script: never write "EXT.", "INT.", "CUT TO", "FADE IN" or a heading as a Visual step.
- Every Visual step names a character from Characters (or "the narrator") and an object from Objects, doing something.
- Keep the same character names and looks across scenes. Same language as the topic. No emojis.

Example of ONE scene (shape only, invent your own content):
{{"title": "The test", "place": "an outdoor shooting range with straw targets and sandbags", "time": "day",
  "characters": [{{"name": "Marcus", "looks": "a Roman legionnaire in red tunic and steel helmet"}}, {{"name": "Dr. Lee", "looks": "a scientist in a white lab coat with goggles"}}],
  "objects": ["a 9mm pistol", "a lorica segmentata breastplate on a wooden stand"],
  "visual": ["Dr. Lee hangs the breastplate on the wooden stand", "Dr. Lee fires the 9mm pistol at the breastplate", "The bullet hits the steel in slow motion and sparks fly", "Marcus leans in and points at the dent"],
  "camera": ["wide", "side view", "extreme close-up", "medium"], "music": "tense", "sfx": "gunshot, metal clang",
  "narrator": "So scientists fired a real bullet at it.", "dialogue": [{{"name": "Marcus", "say": "It held!"}}]}}

Reply JSON only: {{"title": "under 60 chars", "scenes": [ ...{scenes} scenes like the example... ]}}"""


def _ollama(prompt, n=3000):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt, "format": "json",
                      "stream": False, "options": {"temperature": .8, "num_ctx": 6144, "num_predict": n}}, timeout=1800)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def _clean_step(v):
    """Drop film-script headings the model sometimes writes anyway."""
    v = re.sub(r"^\s*(?:CUT TO|FADE (?:IN|OUT|TO)|DISSOLVE TO)\s*[:\-–—]*\s*", "", str(v).strip(), flags=re.I)
    v = re.sub(r"^\s*(?:EXT|INT)\.?\s*", "", v, flags=re.I)
    v = re.sub(r"\s*[-–—]\s*(?:DAY|NIGHT|DAWN|DUSK|MORNING|EVENING|CONTINUOUS)\s*$", "", v, flags=re.I).strip(" -–—.")
    if not v:
        return None
    if v.isupper() and len(v.split()) <= 6:   # a bare ALL-CAPS heading says nothing to animate
        return "Show " + v.lower() + "."
    return v[0].upper() + v[1:] + ("" if v.endswith((".", "!", "?", '"')) else ".")


def to_text(j):
    """JSON screenplay -> the script-box format the screenplay reader understands (Scene / Place / Time / Characters /
    Objects / Visual / Camera / Music / SFX / Narrator / Dialogue)."""
    out = []
    for i, s in enumerate(j.get("scenes", []), 1):
        vis = [x for x in (_clean_step(v) for v in (s.get("visual") or [])) if x]
        say = re.sub(r"\s+", " ", str(s.get("narrator") or s.get("say") or "")).replace('"', "'").strip()
        dlg = [(str(d.get("name") or "").strip(), re.sub(r"\s+", " ", str(d.get("say") or "")).replace('"', "'").strip())
               for d in (s.get("dialogue") or []) if isinstance(d, dict)]
        dlg = [(n, t) for n, t in dlg if n and t]
        spk = str(s.get("speaker") or "Narrator").strip() or "Narrator"
        if not say and not dlg:
            continue
        cam = s.get("camera") or []
        cam = [cam] if isinstance(cam, str) else cam
        chars = [c for c in (s.get("characters") or []) if isinstance(c, dict) and c.get("name")]
        objs = [str(o).strip() for o in (s.get("objects") or []) if str(o).strip()]
        out.append(f"Scene {i} – {str(s.get('title') or f'Scene {i}').strip()}")
        if s.get("place"):
            out.append(f"Place: {str(s['place']).strip()}")
        if s.get("time"):
            out.append(f"Time: {str(s['time']).strip()}")
        if chars:
            out.append("Characters:\n" + "\n".join(f"- {c['name']}: {str(c.get('looks') or '').strip()}" for c in chars))
        if objs:
            out.append("Objects: " + "; ".join(objs))
        out.append("Visual:\n" + "\n".join(f"- {v}" for v in vis))
        if cam:
            out.append("Camera:\n" + "\n".join(f"- {c}" for c in cam))
        if s.get("music"):
            out.append(f"Music: {s['music']}")
        if s.get("sfx"):
            out.append(f"SFX: {s['sfx']}")
        if say:
            out.append(f'{"Narrator" if spk.lower() == "narrator" else spk}: "{say}"')
        for n, t in dlg:
            out.append(f'Dialogue – {n}: "{t}"')
        out.append("")
    return "\n".join(out)


def write(topic, secs, mode, g, inspo=()):
    """-> screenplay text (or None if the LLM isn't available)."""
    words = int(secs * 2.5); scenes = max(3, min(24, round(secs / 7))); per = max(8, round(words / scenes))
    p = PROMPT.format(style=STYLE.get(mode, STYLE["cinema"]), topic=topic, tone=g.get("tone", ""), secs=secs, words=words, scenes=scenes, per=per,
                      inspo=("Inspiration (do not copy): " + "; ".join(inspo)) if inspo else "")
    for attempt in range(3):
        try:
            j = _ollama(p, n=min(9000, 800 + scenes * 380))
            text = to_text(j)
            spoken = sum(len(m.split()) for m in re.findall(r':\s*"([^"]+)"', text))
            steps = sum(len([v for v in (sc.get("visual") or []) if _clean_step(v)]) for sc in j.get("scenes", [])); nsc = max(1, len(j.get("scenes", [])))
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
