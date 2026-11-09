"""Builds NEW objects and creatures for whatever a script names (cinema mode), instead of relying on a fixed list.
The free local LLM (Ollama, on the runner) turns each scene's Visual steps into build recipes made of primitive shapes
(box, sphere, cylinder, cone, torus, capsule, plane, text) with colours, glow, transparency and a motion; creatures
become rig parameters for the engine's animal / person / bird / fish rigs. Recipes are cached by name so a "time
machine" is designed once and reused. Without the LLM a readable stand-in is built from the words themselves."""
import json, os, re, requests
from common import load_config, WORK

CACHE = WORK / "object_recipes.json"
SHAPES = ["box", "sphere", "cylinder", "cone", "torus", "capsule", "plane", "text"]
MOTIONS = ["none", "spin", "bob", "pulse", "swing", "flicker", "float", "rock", "open", "orbit"]
PROMPT = """You design low-poly 3D props for an animated video. Every prop is built ONLY from simple parts.
Scene steps:
{steps}
Objects the engine can already build (do NOT design these): {known}.
For every OTHER physical object or creature mentioned in the steps, design it. Keep it recognisable with 3-10 parts.
Units are metres; y is up; the object stands on y=0; x is its width, z its depth. Use real-world sizes.
Part shapes: box (size [w,h,d]), sphere (size [r]), cylinder (size [r_top, r_bottom, h]), cone (size [r, h]),
torus (size [r, tube]), capsule (size [r, length]), plane (size [w,h]), text (size [w,h], "text": "WORDS").
Each part: {{"shape": "...", "size": [...], "pos": [x,y,z], "rot": [x,y,z] in radians, "color": "#rrggbb", "glow": 0-2, "opacity": 0.2-1}}.
"motion" is one of: {motions} (what it does in the video, e.g. a fan spins, a heart pulses, a ghost floats).
Creatures (animals, monsters, aliens, robots ...) are NOT parts: give "creature" with
{{"base": "quadruped|biped|bird|fish", "color": "#hex", "color2": "#hex", "length": m, "height": m, "head": m,
  "features": ["mane","trunk","tusks","horns","antlers","wings","long neck","spikes","stripes","spots","long ears","big ears","tail","hump","wool"]}}.
Reply JSON only: {{"items": [{{"step": 0, "name": "two-word name", "motion": "none", "parts": [...]}} or {{"step": 0, "name": "...", "creature": {{...}}}}]}}"""


def _load():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def _save(c):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(c, open(CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def _ollama(prompt):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt, "format": "json",
                      "stream": False, "options": {"temperature": .4, "num_ctx": 4096, "num_predict": 1800}}, timeout=600)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def _num(v, d, lo=.005, hi=40):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return d


def _col(v, d="#9aa3ad"):
    v = str(v or "").strip()
    return v if re.fullmatch(r"#[0-9a-fA-F]{6}", v) else d


def clean_recipe(it):
    """Keep only what the engine understands; clamp sizes so a bad answer can't blow up the scene."""
    if it.get("creature"):
        c = it["creature"]; base = str(c.get("base", "quadruped")).lower()
        return {"creature": {"base": base if base in ("quadruped", "biped", "bird", "fish") else "quadruped", "color": _col(c.get("color"), "#8a7a6a"),
                             "color2": _col(c.get("color2"), "#5a4a3a"), "length": _num(c.get("length"), 1.2, .1, 12), "height": _num(c.get("height"), .8, .05, 8),
                             "head": _num(c.get("head"), .25, .03, 2), "features": [str(f).lower() for f in (c.get("features") or [])][:8]}}
    parts = []
    for p in (it.get("parts") or [])[:12]:
        sh = str(p.get("shape", "box")).lower()
        if sh not in SHAPES:
            continue
        size = [_num(x, .3) for x in (p.get("size") or [.3])][:3]
        pos = [_num(x, 0, -20, 20) for x in (p.get("pos") or [0, 0, 0])][:3] + [0] * (3 - len((p.get("pos") or [])[:3]))
        rot = [_num(x, 0, -7, 7) for x in (p.get("rot") or [0, 0, 0])][:3] + [0] * (3 - len((p.get("rot") or [])[:3]))
        parts.append({"shape": sh, "size": size, "pos": pos, "rot": rot, "color": _col(p.get("color")), "glow": _num(p.get("glow"), 0, 0, 3),
                      "opacity": _num(p.get("opacity"), 1, .1, 1), **({"text": str(p.get("text"))[:40]} if p.get("text") else {})})
    if not parts:
        return None
    mo = str(it.get("motion", "none")).lower()
    return {"parts": parts, "motion": mo if mo in MOTIONS else "none"}


# words that are never props
STOP = set("""a an the of to in on at with and or from into onto over under behind beside near toward towards through across around
show shows introduce display displays make makes cut transition return suddenly slowly finally then while as is are be being its his her their
this that these those some another other one two three four five scene camera shot close-up wide medium zoom background foreground effect
light lights glow glowing subtle soft bright dark colourful colorful slightly gradually animated small large big huge tiny little long short
left right top bottom front back side inside outside middle center centre word words letter letters text title sentence fine print
""".split())


VERBS = set("""stands stand sits sit walks walk runs run starts start begins begin appears appear flies fly looks look holds hold carries carry opens open
moves move floats float spins spin glows glow grows grow falls fall jumps jump comes come goes go turns turn waits wait watches watch lies lie rests rest
shines shine flashes flash rises rise sinks sink breaks break explodes explode lands land enters enter leaves leave pours pour drips drip hangs hang
sleeps sleep eats eat drinks drink talks talk says say points point reaches reach rolls roll slides slide hovers hover beeps beep rings ring
out up down away off back""".split())


PERSON_HEADS = set("""inventor worker teacher student kid child baby boy girl man woman men women people person guy lady king queen prince princess
soldier knight guard pirate sailor captain farmer doctor nurse chef cook driver pilot astronaut wizard witch hero villain thief detective police
officer salesperson businessman scientist scientists researcher engineer professor friend friends crowd family mother father grandpa grandma
stickman character characters figure""".split())


def candidates(step, known_words, strict=True):
    """Noun phrases in a step ('a glowing time machine' -> 'time machine'; 'a unicorn walks' -> 'unicorn').
    strict: leave out people and anything whose head noun the library already builds."""
    t = re.sub(r'"[^"]*"', " ", step.lower()); toks = re.sub(r"[^a-z\s-]", " ", t).split()
    out = []
    for i, w in enumerate(toks):
        if w not in ("a", "an", "the", "two", "three", "some"):
            continue
        words = []
        for x in toks[i + 1:i + 6]:
            if x in VERBS or x in ("a", "an", "the", "of", "with", "and", "on", "in", "at", "beside", "near", "from", "to", "into", "behind", "while", "as") \
                    or (words and (x.endswith("ing") or (x.endswith("s") and not x.endswith("ss") and len(words) >= 1 and x not in known_words))):
                break
            if x not in STOP:
                words.append(x)
        if not words:
            continue
        phrase = " ".join(words[-2:]); head = words[-1]
        if len(phrase) < 3:
            continue
        if strict and (head in PERSON_HEADS or head in known_words or head.rstrip("s") in known_words or phrase in known_words):
            continue
        out.append(phrase)
    return list(dict.fromkeys(out))[:4]


def stand_in(name):
    """No LLM: a readable placeholder built from the words (shape from the noun, colour from the adjectives)."""
    n = name.lower(); col = next((c for w, c in (("red", "#d8312b"), ("blue", "#2f63c9"), ("green", "#3fa35b"), ("gold", "#e6b422"), ("black", "#2a2a33"),
                                                 ("white", "#eeeeee"), ("silver", "#b8c0c8"), ("wood", "#8a5a2a"), ("glass", "#cfefff")) if w in n), "#9aa3ad")
    if any(w in n for w in ("ball", "orb", "planet", "egg", "bubble", "globe")):
        parts = [{"shape": "sphere", "size": [.3], "pos": [0, .3, 0], "rot": [0, 0, 0], "color": col, "glow": .4 if "glow" in n else 0, "opacity": 1}]
    elif any(w in n for w in ("tower", "pillar", "bottle", "can", "tube", "pipe", "candle", "rocket")):
        parts = [{"shape": "cylinder", "size": [.15, .18, .9], "pos": [0, .45, 0], "rot": [0, 0, 0], "color": col, "glow": 0, "opacity": 1},
                 {"shape": "cone", "size": [.17, .3], "pos": [0, 1.05, 0], "rot": [0, 0, 0], "color": "#d8312b", "glow": 0, "opacity": 1}]
    else:
        parts = [{"shape": "box", "size": [.8, .6, .6], "pos": [0, .3, 0], "rot": [0, 0, 0], "color": col, "glow": 0, "opacity": 1}]
    parts.append({"shape": "text", "size": [1.1, .25], "pos": [0, parts[-1]["pos"][1] + .55, 0], "rot": [0, 0, 0], "color": "#ffffff", "glow": 0, "opacity": 1, "text": name.upper()})
    return {"parts": parts, "motion": "none", "standin": True}


def design(beats, known_words, use_llm=True):
    """-> {step index: [{"name", "recipe"}]} for objects/creatures the library can't build. Cached by name."""
    cache = _load(); guess = {i: candidates(b, known_words) for i, b in enumerate(beats)}
    want = {i: [n for n in candidates(b, known_words, strict=False) if n in cache] for i, b in enumerate(beats)}   # designed before (any head noun)
    missing = sorted({n for ns in guess.values() for n in ns if n not in cache})
    llm_ok = False
    if missing and use_llm:
        try:
            steps = "\n".join(f"{i}. {b}" for i, b in enumerate(beats))
            res = _ollama(PROMPT.format(steps=steps, known=", ".join(sorted(known_words))[:600], motions=", ".join(MOTIONS)))
            for it in res.get("items", []) if isinstance(res, dict) else []:
                nm = re.sub(r"\s+", " ", str(it.get("name", "")).lower()).strip()[:40]; rc = clean_recipe(it)
                if nm and rc:
                    cache[nm] = rc
                    step = it.get("step")
                    if isinstance(step, int) and 0 <= step < len(beats) and nm not in want.get(step, []):
                        want.setdefault(step, []).append(nm)
            _save(cache); llm_ok = True
        except Exception as e:
            print(f"  object designer (LLM) unavailable ({type(e).__name__}); using stand-ins", flush=True)
    if not llm_ok and missing:   # no designer: readable stand-ins for the clearest nouns only
        for i, ns in guess.items():
            want[i] = list(dict.fromkeys(want.get(i, []) + [n for n in ns if n not in cache][:1]))
    out = {}
    for i, names in want.items():
        for n in names:
            rc = cache.get(n) or next((cache[k] for k in cache if k in n or n in k), None) or stand_in(n)
            out.setdefault(i, []).append({"name": n, "recipe": rc})
    made = sorted({o["name"] for v in out.values() for o in v})
    if made:
        print("  new objects designed for this script: " + ", ".join(made), flush=True)
    return out
