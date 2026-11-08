"""2D mode: flat-vector animated story (original cartoon characters, HUD, maps, checklists, radio messages,
chips, end-card vote). The LLM writes a structured story; every frame is drawn in code by toon/toon.html.
Each character gets its own free Edge voice, and the line's emotion changes speed/pitch."""
import json, os, random, re, subprocess
import requests
from common import load_config, ROOT

SHOTS = ["char", "map", "checklist", "chips", "message", "stat", "black"]
PLACES = ["mountains", "forest", "snow", "road", "city", "house", "room", "office", "cabin", "vehicle", "desert", "sea", "cave", "space", "school"]
WEATHER = ["clear", "snow", "blizzard", "rain", "storm", "fog"]
EMO = ["calm", "scared", "happy", "angry", "sad"]

PROMPT = """You write a {seconds}-second vertical 2D animated story video. Genre: {genre}. Style: {tone}
Make ONE completely original story (never copy existing characters or videos). Idea: {idea}
{inspo}
It is told by a narrator in short punchy lines (6-16 words), present tense, with a ticking clock and rising stakes,
like a survival "what would you do" story. Characters may speak a few lines themselves.
Every line picks a visual "shot":
 char (a character on screen), map (route on a map; data: from, to), checklist (data: title, items list of 3 short words),
 chips (data: items list of 2-3 short facts like "400 CANS OF SOUP"), message (radio/phone; data: from, text),
 stat (big number; data: value, label), black (dark pause).
"place" is one of: {places}. "weather" is one of: {weather}. "emotion" is one of: {emo}.
"time" is a clock like "11:40 PM" that moves forward through the story. "temp" like "4°F".
End with a two-option question for viewers.
Reply with JSON only, exactly this shape:
{{"title": "under 60 chars", "description": "2 sentences", "tags": ["5-8 tags"], "thumb_text": "2-4 WORDS",
  "location": "PLACE NAME · DETAIL", "hook_title": "3-5 WORD QUESTION?",
  "characters": [{{"name": "...", "gender": "male|female", "age": "child|adult|old", "hair": "color", "outfit": "short description", "pet": "dog|cat|none"}}],
  "lines": [{{"say": "...", "speaker": "narrator or a character name", "shot": "char", "place": "road", "weather": "snow",
              "time_of_day": "night|day|dusk|dawn", "time": "11:40 PM", "temp": "4°F", "emotion": "calm", "hl": "KEYWORD", "data": {{}}}}],
  "choice": {{"question": "WHAT DOES <NAME> DO?", "a": "2 WORDS", "b": "2 WORDS"}}}}
Write about {lines} lines."""

MORE = """Continue this {genre} 2D animated story with about {lines} more lines in the same JSON line format
(say, speaker, shot, place, weather, time_of_day, time, temp, emotion, hl, data). Keep the same characters: {names}.
Move the story forward toward the final question "{question}". Story so far (last lines): {last}
Reply with JSON only: {{"lines": [...]}}"""

HAIR = {"black": "#1d1a1a", "brown": "#5a3a22", "blonde": "#e0b85a", "blond": "#e0b85a", "red": "#a8432a", "ginger": "#c0602f",
        "gray": "#9a9a9f", "grey": "#9a9a9f", "white": "#e8e8e8", "silver": "#c8c8cf", "blue": "#3a5bd0", "pink": "#e07aa8", "purple": "#7a4ab0"}
COLORS = {"red": "#c0392b", "yellow": "#f2c230", "green": "#2f8f4e", "blue": "#2f5fa8", "navy": "#1f2d55", "black": "#23232b",
          "white": "#e9e9ee", "gray": "#7a7f8a", "grey": "#7a7f8a", "orange": "#e07a2f", "purple": "#6a3fa0", "pink": "#e07aa8",
          "brown": "#7a4a2a", "teal": "#2a8f8f", "maroon": "#7a1f2b"}
SKINS = ["#f1c7a0", "#e0ac7e", "#c68a5a", "#9c6a42", "#6f4a30", "#f6d4b8"]
VOICES = {("male", "adult"): ["en-US-EricNeural", "en-US-RogerNeural", "en-US-SteffanNeural"],
          ("female", "adult"): ["en-US-JennyNeural", "en-US-MichelleNeural", "en-GB-SoniaNeural"],
          ("male", "old"): ["en-GB-RyanNeural"], ("female", "old"): ["en-GB-SoniaNeural"],
          ("male", "child"): ["en-US-AnaNeural"], ("female", "child"): ["en-US-AnaNeural"]}
MOOD = {"calm": ("+0%", "+0Hz"), "scared": ("+10%", "+3Hz"), "happy": ("+6%", "+4Hz"), "angry": ("+6%", "-2Hz"), "sad": ("-10%", "-3Hz")}


def _ollama(prompt, n=2500):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt,
                      "format": "json", "stream": False, "options": {"temperature": 0.85, "num_ctx": 4096, "num_predict": n}}, timeout=1500)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def _pick(v, allowed, default):
    v = str(v or "").lower().strip()
    return v if v in allowed else next((a for a in allowed if a in v), default)


def _look(ch, i):
    """Turn a short text description into drawing parameters (original flat-vector look)."""
    rng = random.Random(f"{ch.get('name')}{i}"); outfit = str(ch.get("outfit", "")).lower(); hair = str(ch.get("hair", "")).lower()
    gender = _pick(ch.get("gender"), ["male", "female"], "male"); age = _pick(ch.get("age"), ["child", "adult", "old"], "adult")
    col = next((v for k, v in COLORS.items() if k in outfit), rng.choice(list(COLORS.values())[:12]))
    hat = "cap" if "cap" in outfit else "beanie" if ("beanie" in outfit or "wool hat" in outfit) else "hood" if "hood" in outfit else (rng.choice(["cap", "beanie", None, None]) if gender == "male" else None)
    pattern = "plaid" if ("plaid" in outfit or "flannel" in outfit) else "stripe" if "stripe" in outfit else "coat" if any(w in outfit for w in ("coat", "jacket", "raincoat", "parka")) else rng.choice(["plain", "plaid", "coat"])
    return {"name": ch.get("name") or f"Hero{i}", "gender": gender, "age": age,
            "skin": rng.choice(SKINS), "hair": next((v for k, v in HAIR.items() if k in hair), "#3a2a1e" if age != "old" else "#c8c8cf"),
            "hairStyle": ("long" if gender == "female" and rng.random() < 0.6 else "bun" if gender == "female" else rng.choice(["short", "short", "curly", "bald" if age == "old" else "short"])),
            "hat": hat, "hatColor": rng.choice(["#2f6b3f", "#2f4f8f", "#8f2f2f", "#d9a23a"]), "top": col, "pattern": pattern,
            "beard": gender == "male" and age != "child" and rng.random() < 0.55,
            "pet": _pick(ch.get("pet"), ["dog", "cat", "none"], "none") if i == 0 else "none"}


def _clean_line(l, prev):
    say = re.sub(r"\s+", " ", str(l.get("say", ""))).strip().strip('"')
    if not say:
        return None
    d = l.get("data") if isinstance(l.get("data"), dict) else {}
    out = {"say": say, "speaker": str(l.get("speaker") or "narrator"), "shot": _pick(l.get("shot"), SHOTS, "char"),
           "place": _pick(l.get("place"), PLACES, prev.get("place", "road")), "weather": _pick(l.get("weather"), WEATHER, prev.get("weather", "clear")),
           "time_of_day": _pick(l.get("time_of_day"), ["night", "day", "dusk", "dawn"], prev.get("time_of_day", "night")),
           "emotion": _pick(l.get("emotion"), EMO, "calm"), "hl": [str(l.get("hl") or max(say.split(), key=len)).upper().strip(".,!?")]}
    for k in ("time", "temp"):
        if l.get(k):
            out[{"time": "clock", "temp": "temp"}[k]] = str(l[k]).upper()[:10]
    if out["shot"] == "checklist":
        items = [str(x)[:16] for x in (d.get("items") or [])][:4] or ["SHELTER", "FOOD", "HEAT"]
        out["data"] = {"title": str(d.get("title") or "THE PLAN")[:22], "items": items, "checked": 1}
    elif out["shot"] == "chips":
        out["data"] = {"items": [str(x)[:22] for x in (d.get("items") or [])][:3] or [out["hl"][0]]}
    elif out["shot"] == "map":
        out["data"] = {"from": str(d.get("from") or "TOWN")[:14], "to": str(d.get("to") or "DESTINATION")[:16]}
    elif out["shot"] == "message":
        out["data"] = {"from": str(d.get("from") or "RADIO")[:18], "text": str(d.get("text") or say)[:90], "channel": str(d.get("channel") or "19")[:3]}
    elif out["shot"] == "stat":
        out["data"] = {"value": str(d.get("value") or out["hl"][0])[:10], "label": str(d.get("label") or "")[:24]}
    return out


def write_story(g, idea, inspo, minutes=0):
    seconds = int(minutes * 60) if minutes else 55
    want_words = seconds * 2.5; n_lines = max(10, round(want_words / 10))
    ins = ("Trending titles (tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
    story = None
    for attempt in range(3):
        try:
            story = _ollama(PROMPT.format(seconds=seconds, genre=g["name"], tone=g["tone"], idea=idea, inspo=ins, lines=min(n_lines, 16),
                                          places=", ".join(PLACES), weather=", ".join(WEATHER), emo=", ".join(EMO)))
            if story.get("lines"):
                break
        except Exception as e:
            print(f"  2d story retry ({e})")
    if not story or not story.get("lines"):
        raise SystemExit("The 2D story writer (Ollama) failed. Nothing was uploaded. Please run again.")
    chars = [c for c in story.get("characters", []) if isinstance(c, dict)][:3] or [{"name": "Sam", "gender": "male", "outfit": "plaid shirt, cap", "pet": "dog"}]
    choice = story.get("choice") if isinstance(story.get("choice"), dict) else {}
    question = str(choice.get("question") or "WHAT WOULD YOU DO?")[:40]
    raw = [l for l in story["lines"] if isinstance(l, dict)]
    for attempt in range(6):   # small local models write short JSON; keep asking for more until long enough
        if sum(len(str(l.get("say", "")).split()) for l in raw) >= want_words * 0.85:
            break
        try:
            more = _ollama(MORE.format(genre=g["name"], lines=10, names=", ".join(c.get("name", "") for c in chars), question=question,
                                       last=" ".join(str(l.get("say", "")) for l in raw[-4:])), 1800)
            new = [l for l in more.get("lines", []) if isinstance(l, dict)]
            if not new:
                break
            raw += new
        except Exception as e:
            print(f"  2d continue retry ({e})")
    lines, prev = [], {}
    for l in raw:
        c = _clean_line(l, prev)
        if c:
            lines.append(c); prev = c
    lines[0]["shot"] = "char"
    a, b = str(choice.get("a") or "STAY")[:14], str(choice.get("b") or "GO")[:14]
    lines.append({"say": f"{question.capitalize()} {a.lower()}, or {b.lower()}? Vote in the comments.", "speaker": "narrator", "shot": "choice",
                  "place": prev.get("place", "road"), "weather": prev.get("weather", "clear"), "time_of_day": prev.get("time_of_day", "night"),
                  "emotion": "calm", "hl": ["COMMENTS."]})
    cast = [_look(c, i) for i, c in enumerate(chars)]
    # voices: narrator = genre voice, each character a different free Edge voice; mood changes speed/pitch
    used = {g.get("voice", {}).get("edge_voice")}; vmap = {}
    for c in cast:
        opts = [v for v in VOICES.get((c["gender"], c["age"]), VOICES[("male", "adult")]) if v not in used] or VOICES[("male", "adult")]
        vmap[c["name"].lower()] = opts[0]; used.add(opts[0])
    for ln in lines:
        rate, pitch = MOOD.get(ln["emotion"], MOOD["calm"])
        v = vmap.get(ln["speaker"].lower())
        if v:
            ln.update(voice=v, rate=rate, pitch=pitch)
        elif ln["emotion"] in ("scared", "sad"):
            ln.update(rate=MOOD[ln["emotion"]][0])
    print(f"  2d story: {story.get('title')!r}, {len(lines)} lines, cast: " + ", ".join(f"{c['name']} ({vmap.get(c['name'].lower())})" for c in cast))
    return {"title": str(story.get("title") or idea)[:70], "description": str(story.get("description") or idea),
            "tags": [str(t) for t in story.get("tags", [])][:10], "thumb_text": str(story.get("thumb_text") or question)[:24],
            "lines": lines, "cast": cast, "choice": {"question": question, "a": a, "b": b},
            "hud": {"location": str(story.get("location") or "UNKNOWN")[:34].upper(), "day": "DAY 1", "part": "PART 1",
                    "title": str(story.get("hook_title") or f"{a} OR {b}?")[:26].upper()}}


def render(sc, tl, d, g, preview=False):
    """tl = timeline from timeline.build_timeline (segs carry shot/place/... fields). Writes d/video.mp4."""
    accent = g.get("thumb_color", "#e0262f"); hl = "#ffd23f" if accent.lower() != "#ffe500" else "#ffffff"
    toon = {"segs": tl["segs"], "total": tl["total"], "cast": sc["cast"], "hud": sc["hud"], "choice": sc["choice"],
            "style": {"accent": "#e0262f" if g["name"] in ("horror", "mystery") else accent, "hl": hl}}
    json.dump(toon, open(os.path.join(d, "toon.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"))
    args = ["node", str(ROOT / "toon" / "render.js"), d] + (["preview", "1", "5", "9", str(tl["total"] - 1)] if preview else [])
    subprocess.run(args, check=True, env=env)
