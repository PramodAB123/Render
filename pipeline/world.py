"""Cinema mode built from the script: reads who/what is in each line (animals, people, creatures, vehicles), what they
do (walk, run, roar, fly, sleep ...), where it happens (savanna, jungle, ocean, city, space ...), time of day and weather,
then hands that plan to code-cinema/engine/world.html, which assembles every model in code and films it with the
skill's camera-angle library. No preset scene: a lion script gives you a lion on the savanna."""
import json, os, re, shutil, subprocess
from common import CINEMA, ROOT, FFMPEG
import design

# words -> actor type the engine can build (checked longest first, so "polar bear" beats "bear")
ACTORS = {
    "lioness": "lioness", "lion": "lion", "tiger": "tiger", "leopard": "leopard", "cheetah": "cheetah", "panther": "leopard", "jaguar": "leopard",
    "kitten": "cat", "cat": "cat", "puppy": "dog", "dog": "dog", "wolf": "wolf", "wolves": "wolf", "fox": "fox", "horse": "horse", "pony": "horse",
    "zebra": "zebra", "giraffe": "giraffe", "elephant": "elephant", "rhino": "rhino", "hippo": "hippo", "polar bear": "polar", "bear": "bear",
    "cow": "cow", "bull": "bull", "pig": "pig", "sheep": "sheep", "lamb": "sheep", "goat": "goat", "deer": "deer", "stag": "deer", "camel": "camel",
    "rabbit": "rabbit", "bunny": "rabbit", "hare": "rabbit", "mouse": "mouse", "mice": "mouse", "rat": "mouse", "dragon": "dragon",
    "dinosaur": "dinosaur", "t-rex": "dinosaur", "trex": "dinosaur", "crocodile": "crocodile", "alligator": "crocodile", "monkey": "monkey", "ape": "monkey",
    "gorilla": "monkey", "chimp": "monkey", "eagle": "eagle", "hawk": "eagle", "owl": "owl", "parrot": "parrot", "crow": "crow", "raven": "crow",
    "penguin": "penguin", "duck": "duck", "chicken": "chicken", "hen": "chicken", "rooster": "chicken", "bat": "bat", "bird": "bird", "sparrow": "bird",
    "shark": "shark", "whale": "whale", "dolphin": "dolphin", "fish": "fish", "car": "car", "truck": "truck", "robot": "robot", "ghost": "ghost",
    "शेर": "lion", "बाघ": "tiger", "हाथी": "elephant", "कुत्ता": "dog", "बिल्ली": "cat", "बंदर": "monkey", "घोड़ा": "horse", "भालू": "bear", "भेड़िया": "wolf",
    "लोमड़ी": "fox", "चूहा": "mouse", "खरगोश": "rabbit", "हिरण": "deer", "गाय": "cow", "मछली": "fish", "पक्षी": "bird", "चिड़िया": "bird", "मगरमच्छ": "crocodile",
    "ड्रैगन": "dragon", "भूत": "ghost", "रोबोट": "robot",
}
HOME = {"lion": "savanna", "lioness": "savanna", "zebra": "savanna", "giraffe": "savanna", "elephant": "savanna", "cheetah": "savanna", "rhino": "savanna",
        "hippo": "savanna", "leopard": "jungle", "tiger": "jungle", "monkey": "jungle", "parrot": "jungle", "crocodile": "jungle", "wolf": "forest",
        "fox": "forest", "deer": "forest", "bear": "forest", "owl": "forest", "rabbit": "forest", "polar": "snow", "penguin": "snow", "camel": "desert",
        "shark": "underwater", "whale": "ocean", "dolphin": "ocean", "fish": "underwater", "cow": "farm", "bull": "farm", "pig": "farm", "sheep": "farm",
        "goat": "farm", "chicken": "farm", "duck": "farm", "horse": "farm", "dragon": "castle", "dinosaur": "jungle", "car": "city", "truck": "city",
        "robot": "city", "ghost": "graveyard", "bat": "cave"}
PLACES = [  # (words, env) - the place the scene names first wins; scenes that name none stay where they were
    (("savanna", "savannah", "grassland", "plains", "pride rock", "african"), "savanna"), (("jungle", "rainforest", "जंगल"), "jungle"),
    (("forest", "woods", "trees"), "forest"), (("desert", "sand dunes", "रेगिस्तान"), "desert"), (("snow", "arctic", "ice", "frozen", "glacier", "बर्फ"), "snow"),
    (("underwater", "under the sea", "coral", "reef", "seabed"), "underwater"), (("beach", "shore", "coast", "island"), "beach"), (("ship", "deck", "boat", "जहाज"), "ship"),
    (("ocean", "sea", "waves", "समुद्र"), "ocean"), (("city", "street", "town", "building", "road", "शहर"), "city"), (("village", "गांव"), "village"),
    (("farm", "barn", "field", "खेत"), "farm"), (("mountain", "cliff", "peak", "hill", "पहाड़"), "mountain"), (("cave", "tunnel", "गुफा"), "cave"),
    (("outer space", "in space", "galaxy", "planet", "rocket", "spaceship", "अंतरिक्ष"), "space"), (("moon",), "moon"), (("castle", "kingdom", "palace", "throne", "महल"), "castle"),
    (("graveyard", "cemetery", "grave", "कब्रिस्तान"), "graveyard"), (("room", "house", "home", "kitchen", "bedroom", "office", "घर", "कमरा"), "room"),
    (("river", "lake", "waterhole", "pond", "नदी"), "savanna"),
]
ACTIONS = [  # (words, action) - first hit wins for each line
    (("roar", "roars", "roared", "growl", "दहाड़"), "roar"), (("chase", "chases", "chasing", "hunt", "hunts", "pounce"), "chase"),
    (("run", "runs", "running", "ran", "sprint", "flee", "escape", "charges", "dash", "भाग"), "run"),
    (("fight", "fights", "attack", "attacks", "bite", "bites", "strike", "battle", "clash", "लड़"), "attack"),
    (("fly", "flies", "flying", "flew", "soar", "soars", "उड़"), "fly"), (("swim", "swims", "swimming", "dive", "तैर"), "swim"),
    (("jump", "jumps", "leap", "leaps", "hop", "कूद"), "jump"), (("sleep", "sleeps", "asleep", "rest", "rests", "nap", "lies down", "सो"), "sleep"),
    (("eat", "eats", "eating", "drink", "drinks", "feast", "graze", "खा"), "eat"), (("sit", "sits", "sitting", "बैठ"), "sit"),
    (("walk", "walks", "walking", "wander", "stroll", "march", "enter", "enters", "चल"), "walk"), (("drive", "drives", "driving"), "drive"),
    (("look", "looks", "watch", "watches", "stare", "notice", "देख"), "look"), (("scared", "afraid", "fear", "tremble", "hide", "डर"), "scared"),
    (("dance", "celebrate", "happy", "laugh", "cheer", "खुश"), "happy"),
]
TOD = [(("night", "midnight", "moonlight", "रात"), "night"), (("sunset", "dusk", "evening", "शाम"), "dusk"), (("dawn", "sunrise", "morning", "सुबह"), "dawn")]
WEATHER = [(("rain", "storm", "बारिश"), "rain"), (("lightning", "thunder"), "lightning"), (("snow", "blizzard"), "snow"), (("fog", "mist"), "fog")]
SHOT_CYCLE = ["low_hero", "orbit", "wide", "dolly_in", "over_shoulder", "aerial", "dutch", "pull_back"]


def _has(t, w):
    if re.search(r"[ऀ-ॿ]", w):
        return w in t
    return re.search(r"(?<![a-z])" + re.escape(w) + r"s?(?![a-z])", t) is not None


def _first(t, table):
    hits = [(min(t.find(w) for w in ws if _has(t, w)), v) for ws, v in table if any(_has(t, w) for w in ws)]
    return min(hits)[1] if hits else None


def _actors_in(t):
    out = []
    for w in sorted(ACTORS, key=len, reverse=True):
        if _has(t, w):
            ty = ACTORS[w]
            if ty not in [a for a, _ in out]:
                out.append((ty, t.find(w)))
            t = t.replace(w, " " * len(w))
    return [ty for ty, _ in sorted(out, key=lambda x: x[1])]


def plan(sc, tl, g):
    """Per timeline segment: env, tod, weather, actors (built once per scene), what each one does, and the camera angle."""
    lines, segs = sc["lines"], tl["segs"]
    cast = sc.get("cast", [])
    everything = " ".join(str(l.get("scene_visual") or l.get("image") or "") + " " + str(l.get("say", "")) for l in lines).lower()
    everything += " " + str(sc.get("title", "")).lower() + " " + str(sc.get("description", "")).lower()
    # cast: named characters (an animal name makes them that animal, otherwise a person designed from the script) + creatures named
    roster = []
    spoken_by = {str(l.get("speaker", "")).lower() for l in lines}
    for i, c in enumerate(cast):
        nm = str(c.get("name", ""))
        if nm.lower() not in spoken_by and not _has(everything, nm.lower()):
            continue
        ty = next((ACTORS[w] for w in sorted(ACTORS, key=len, reverse=True) if _has(nm.lower(), w)), None)
        roster.append({"name": nm, "type": ty or ("ghost" if c.get("ghost") else "person"), **{k: c.get(k) for k in ("cols", "costume", "extras", "prop", "size", "ghost", "glow")},
                       "female": c.get("gender") == "female"})
    for ty in _actors_in(everything):
        if ty not in [r["type"] for r in roster]:
            roster.append({"name": ty, "type": ty})
    if not any(r["type"] == "person" for r in roster):
        roster.append({"name": "person", "type": "person", "cols": ["#2f63c9", "#2f63c9"]})
    habitat = next((HOME[r["type"]] for r in roster if r["type"] in HOME), None)
    env, tod, scene_no, shot_k, prev_scene = habitat or ("room" if any(l.get("beats") for l in lines) else "savanna"), "day", -1, 0, None
    prev_cast = [0]
    for i, (ln, sg) in enumerate(zip(lines, segs)):
        vis = str(ln.get("scene_visual") or ln.get("image") or "").lower(); say = str(ln.get("say", "")).lower(); t = vis + " " + say
        sid = ln.get("scene", i if not vis else vis[:60])
        new_scene = sid != prev_scene; prev_scene = sid
        if new_scene:
            env = _first(vis, PLACES) or _first(say, PLACES) or env
            tod = _first(vis, TOD) or ("night" if env in ("space", "moon", "graveyard") else "day")
            scene_no += 1
        # who is in this shot: named in the line / speaking, else the last shot's cast
        here = []
        spk = str(ln.get("speaker", "")).lower()
        for k, r in enumerate(roster):
            nm = r["name"].lower()
            if (nm and nm != r["type"] and _has(t, nm)) or (r["type"] != "person" and _has(t, r["type"])) or (spk and spk == nm) or any(_has(t, w) for w, v in ACTORS.items() if v == r["type"] and r["name"] == r["type"]):
                here.append(k)
        if re.match(r"\s*(he|she|it|they|him|her|his|its)\b", say) or re.search(r"(?<![a-z])(he|she|it|they)\s+(walks?|runs?|roars?|sleeps?|looks?|jumps?|flies|eats?)", say):
            here = list(dict.fromkeys(prev_cast[:1] + here))   # "He walks to the waterhole" keeps the last subject in shot
        here = here[:4] or (prev_cast if any(roster[k]["type"] != "person" or roster[k]["name"] != "person" for k in prev_cast) else []); prev_cast = here or prev_cast
        action = _first(t, ACTIONS) or ("swim" if env in ("underwater", "ocean") and any(roster[k]["type"] in ("fish", "shark", "whale", "dolphin") for k in here) else "idle")
        weather = sorted({v for ws, v in WEATHER if any(_has(vis, w) for w in ws)} | ({"snow"} if env == "snow" else set()))
        # the camera: open wide, roars and shouts in close-up, movement tracked, two characters framed together
        if i == 0:
            shot = "establishing"
        elif action == "roar" or ("!" in say and action not in ("run", "chase", "fly")):
            shot = "closeup"
        elif action in ("run", "chase", "walk", "fly", "swim", "drive"):
            shot = "tracking"
        elif len(here) > 1 and spk:
            shot = "two_shot"
        else:
            shot = SHOT_CYCLE[shot_k % len(SHOT_CYCLE)]; shot_k += 1
        nxt = {"closeup": "low_hero", "tracking": "low_hero", "establishing": "dolly_in", "two_shot": "over_shoulder"}.get(shot, "closeup")
        acts = [action if (spk and roster[k]["name"].lower() == spk) or len(here) == 1 or action in ("run", "walk", "chase", "fly", "swim", "sleep", "happy", "scared") else ("look" if action != "idle" else "idle") for k in here]
        # an attack/chase needs a target: everyone acts, facing each other
        if action in ("attack", "chase"):
            acts = [action] * len(here)
        steps = None
        if ln.get("beats"):
            steps, env2, tod2 = plan_steps(ln, env, tod, roster, i)
            if steps:
                env, tod = env2, tod2
        sg["world"] = {"scene": scene_no, "env": env, "tod": tod, "weather": weather, "seed": 11 + scene_no * 7, "steps": steps,
                       "actors": [dict(roster[k], dir=1 if j % 2 == 0 else -1) for j, k in enumerate(here)], "acts": acts,
                       "speakerIdx": next((j for j, k in enumerate(here) if spk and roster[k]["name"].lower() == spk), -1),
                       "shot": shot, "shot2": nxt, "action": action, "fx": ln.get("fx") or [], "focus": None if shot in ("two_shot", "establishing", "aerial") else
                       next((j for j, k in enumerate(here) if spk and roster[k]["name"].lower() == spk), 0)}
    summary = ", ".join(f"{r['name']} ({r['type']})" for r in roster)
    print(f"  cinema world: cast {summary}; places " + " > ".join(dict.fromkeys(s["world"]["env"] for s in segs)), flush=True)
    return roster


# ------------------------------------------------------------------ step-by-step planning (each Visual step is its own shot)
STEP_PLACES = [  # checked before PLACES; first mentioned wins
    (("laboratory", "lab ", " lab", "experiment room", "workbench", "प्रयोगशाला"), "lab"), (("office", "company", "headquarters", "reception", "दफ्तर"), "office"),
    (("hallway", "corridor", "hall "), "hallway"), (("garage", "workshop", "factory", "warehouse", "studio", "basement", "attic"), "lab"), (("park", "garden", "playground", "पार्क"), "park"),
    (("virtual", "game-like", "digital world", "video game", "simulation", "metaverse"), "virtual"), (("street", "road", "sidewalk", "outdoor", "सड़क"), "street"),
]
OBJECTS = [  # words -> object the engine builds
    (("jar",), "jar"), (("computer", "monitor", "screen", "laptop", "interface", "कंप्यूटर"), "computer"),
    (("workbench", "table", "desk", "counter"), "bench"), (("shelves", "shelf", "bookcase"), "shelf"),
    (("machine", "equipment", "device", "oxygen supply", "generator", "मशीन"), "machine"), (("bicycle", "bike", "cycle", "साइकिल"), "bicycle"),
    (("contract", "document", "form", "paper", "letter", "fine print", "clause", "consent"), "document"), (("sign", "billboard", "banner", "logo"), "sign"),
    (("finish line", "finish-line", "checkered"), "finish"), (("cable", "wire", "cord"), "cable"), (("chair", "sitting at", "sitting in front"), "chair"),
]
PEOPLE = [  # generic people words -> how they look
    (("scientist", "doctor", "researcher", "lab coat"), {"coat": 1}), (("elderly", "old man", "old woman", "aged", "grandpa", "grandma"), {"old": 1}),
    (("salesperson", "salesman", "businessman", "agent", "manager"), {"cols": ["#2a2e3a", "#2a2e3a"], "costume": "none"}),
    (("thin human", "thin figure", "skinny"), {"thin": 1}), (("creepy", "shadowy", "sinister", "in the shadows"), {"creepy": 1}),
    (("stickman", "stick man", "person", "man", "woman", "boy", "girl", "character", "figure", "someone", "inventor", "worker", "teacher", "student", "kid",
      "engineer", "professor", "astronaut", "pilot", "driver", "chef", "farmer", "detective", "officer", "friend", "crowd"), {}),
]
NUM = {"two": 2, "three": 3, "four": 4, "both": 2, "2": 2, "3": 3, "दो": 2}
STEP_ACTIONS = [(("riding", "rides", "cycling"), "walk"), (("carrying", "carries", "holding", "holds"), "walk"), (("sitting", "sits", "seated"), "sit"),
                (("typing", "working on", "discussing", "observing", "watching"), "look"), (("confused", "shocked", "surprised", "scared", "afraid"), "scared"),
                (("smiling", "happy", "celebrat", "cheer"), "happy"), (("attempting to catch", "chasing", "chase", "catch"), "chase")]
CAMS = [("extreme close", "ecu"), ("close-up", "closeup"), ("close up", "closeup"), ("zoom-out", "pull_back"), ("zoom out", "pull_back"), ("pull back", "pull_back"),
        ("zoom", "dolly_in"), ("push in", "dolly_in"), ("tracking", "tracking"), ("following", "tracking"), ("side-view", "side"), ("side view", "side"),
        ("first-person", "fpv"), ("first person", "fpv"), ("pov", "fpv"), ("medium", "medium"), ("wide", "wide"), ("establishing", "establishing"),
        ("aerial", "aerial"), ("overhead", "aerial"), ("top-down", "aerial"), ("orbit", "orbit"), ("low angle", "low_hero"), ("low-angle", "low_hero"), ("over the shoulder", "over_shoulder")]


def _cam(text):
    t = str(text or "").lower(); hits = [(t.find(k), v) for k, v in CAMS if k in t]
    return min(hits)[1] if hits else None


def _quotes(text):
    return [q.strip() for q in re.findall(r'"([^"]{1,60})"', str(text)) if q.strip()]


def plan_steps(ln, place, tod, roster, idx):
    """One spoken line -> its Visual steps, each with place, people, objects, action and camera."""
    beats = [b for b in (ln.get("beats") or []) if b.strip()] or [str(ln.get("scene_visual") or ln.get("image") or ln.get("say") or "")]
    cams = ln.get("camera") or []
    steps, people_prev, objs_prev = [], None, []
    import makers   # anything the library can't build is designed new for this script
    known = {w.strip() for ws, _ in OBJECTS + STEP_PLACES + PLACES + PEOPLE for w in ws} | set(ACTORS) | {
        "room", "world", "environment", "interface", "information", "effect", "character", "stickman", "scientist", "scientists", "person", "brain",
        "body", "copy", "idea", "experiment", "activity", "nutrients", "oxygen", "air", "data", "message", "error", "notes", "charts", "chart", "detail",
        "shadows", "shadow", "representation", "version", "transition", "section", "signature", "benefits", "memory", "plans", "procedure", "grass", "trees", "tree"}
    designed = makers.design(beats, known)
    for k, b in enumerate(beats):
        t = " " + b.lower() + " "
        if re.search(r"\b(fade to black|fade out)\b", t):
            if steps:
                steps[-1]["fadeOut"] = True
            continue
        tp = t
        m = re.search(r"\b(?:from\b.*?\b(?:to|into)|cut to|return to|back to|transition(?:s)? (?:to|into)|moves? to|switch(?:es)? to)\s+(.*)", t)
        if m:
            tp = " " + m.group(1) + " "
        hits = [(min(tp.find(w) for w in ws if world_has(tp, w)), v) for ws, v in STEP_PLACES + PLACES if any(world_has(tp, w) for w in ws)]
        if hits:
            place = min(hits)[1]
        tod = _first(t, TOD) if any(w in t for w in (" night", "midnight", " moon")) else ("day" if place in ("lab", "office", "virtual", "park", "street") else tod)
        if "dark" in t and place in ("hallway",):
            tod = "night"
        # people: named cast, creatures, or generic people words (with how many)
        people = []
        for j, r in enumerate(roster):
            nm = r["name"].lower()
            if (nm and nm != r["type"] and world_has(t, nm)) or (r["type"] not in ("person",) and world_has(t, r["type"])):
                people.append(dict(r))
        if "banana" in t:
            people.append({"name": "banana", "type": "banana"})
        look = {}
        for ws, lk in PEOPLE:
            if any(world_has(t, w) for w in ws):
                look.update(lk)
        if look or any(world_has(t, w) for ws, _ in PEOPLE for w in ws):
            n = next((v for w, v in NUM.items() if re.search(r"\b" + w + r"\s+(?:stickman\s+|stick\s+)?(scientists|people|men|women|stickmen|characters|persons|figures)", t)), 1)
            if "another character" in t:
                n = 1
            base = next((r for r in roster if r["type"] == "person"), {"name": "person", "type": "person"})
            for q in range(n):
                people.append(dict(base, **look, name=f"{base['name']}{q}" if q else base["name"]))
        if "robot" in t:
            people = [p for p in people if not (p.get("type") == "person" and "robot" in t and "character" in t)] + [{"name": "robot", "type": "robot"}]
        if not people and people_prev and not any(w in t for w in ("screen displays", "close-up of", "zoom into", "display a", "highlight")):
            people = people_prev
        for dsg in designed.get(k, []):
            if dsg["recipe"].get("creature"):
                people.append({"name": dsg["name"], "type": "creature", "recipe": dsg["recipe"]["creature"]})
        people = people[:4]
        # objects named in this step (+ the ones the last step set up, if we're still in the same place)
        objs = []
        for ws, kind in OBJECTS:
            if any(world_has(t, w) for w in ws) and kind not in [o["kind"] for o in objs]:
                objs.append({"kind": kind})
        for dsg in designed.get(k, []):
            if not dsg["recipe"].get("creature"):
                head = dsg["name"].split()[-1]   # 'time machine' replaces the library's generic machine in this step
                objs = [o for o in objs if not any(world_has(" " + head + " ", w) for ws, kd in OBJECTS if kd == o["kind"] for w in ws)]
                objs.append({"kind": "custom", "name": dsg["name"], "recipe": dsg["recipe"]})
        q = _quotes(b)
        for kind in ("sign", "document", "computer"):
            o = next((o for o in objs if o["kind"] == kind), None)
            if o and q:
                o["text"] = q[:3]; q = []
        doc = next((o for o in objs if o["kind"] == "document"), None)
        if doc and ":" in b and not doc.get("text"):
            items = [x.strip(" -.") for x in re.split(r"(?<=[.!?])\s+|\s+-\s+", b.split(":", 1)[1]) if x.strip(" -.")]
            if items:
                doc["text"] = ["LIVE FOREVER"] + items[:3] if any("forever" in str(o.get("text", "")).lower() for o in objs_prev) else items[:4]
        for o in objs:   # the same contract / screen as the last step keeps its words
            old = next((x for x in objs_prev if x["kind"] == o["kind"] and x.get("text")), None)
            if old and not o.get("text"):
                o["text"] = list(old["text"]); o.setdefault("hlLine", old.get("hlLine"))
        if q and not objs:   # "Highlight the sentence: '...'" -> on the document / screen we're already looking at
            prev = next((o for kd in ("document", "computer", "sign") for o in objs_prev if o["kind"] == kd), None)
            if prev:
                prev = dict(prev); prev["text"] = (prev.get("text") or [])[:3] + q[:1]; prev["hlLine"] = len(prev["text"]) - 1
                objs = [prev] + [o for o in objs_prev if o is not prev and o["kind"] != prev["kind"]][:2]; q = []
        if any(o["kind"] == "computer" for o in objs) and "error" in t:
            next(o for o in objs if o["kind"] == "computer").update(error=1, text=(next(o for o in objs if o["kind"] == "computer").get("text") or ["ERROR"]))
        for o in objs:
            if o["kind"] == "document" and not o.get("text"):
                o["text"] = ["CONSENT FORM", "I agree to the procedure", "Signature: __________"] if "consent" in t else ["CONTRACT"] if "contract" in t else []
            if o["kind"] == "computer" and not o.get("text"):
                o.update(text=[], chart="chart" in t or "notes" in t, brainUI="brain" in t)
        if "jar" in [o["kind"] for o in objs] or "brain" in t:
            if not any(o["kind"] == "jar" for o in objs) and not any(o["kind"] == "computer" for o in objs):
                objs.append({"kind": "jar"})
        if q and not objs:   # a quoted word with nothing to show it on -> a screen
            objs.append({"kind": "computer", "text": q[:3]})
        if steps and steps[-1]["env"] == place and not hits:
            keep = [o for o in objs_prev if o["kind"] not in [x["kind"] for x in objs] and not (o["kind"] == "bicycle" and "bicycle" not in t)]
            objs = objs + keep[:max(0, 4 - len(objs))]
        if place in ("lab", "office") and not any(o["kind"] == "bench" for o in objs) and any(o["kind"] in ("jar", "computer") for o in objs):
            objs.insert(0, {"kind": "bench"})
        for o in objs:
            if o["kind"] in ("jar", "computer", "document") and any(x["kind"] == "bench" for x in objs):
                o["onBench"] = 1
        objs = sorted(objs, key=lambda o: 0 if o["kind"] == "bench" else 1)[:5]
        if place == "virtual" and "finish" in t and not any(o["kind"] == "finish" for o in objs):
            objs.append({"kind": "finish"})
        action = _first(t, STEP_ACTIONS) or _first(t, ACTIONS) or "idle"
        if any(o["kind"] == "bicycle" for o in objs) and people:
            action = "ride"; shot = None
            if not _cam(b):
                cams_here = "side"
            else:
                cams_here = None
        # camera: the step's own words, else the Camera line that matches this point of the scene
        cam_line = cams[min(len(cams) - 1, int(k * len(cams) / max(1, len(beats))))] if cams else ""
        if cams and len(cams) == 1 and ("transition" in cams[0].lower() or "followed by" in cams[0].lower() or "," in cams[0]):
            parts = re.split(r"transitioning into|followed by|transition to|then|,", cams[0], flags=re.I)
            cam_line = parts[min(len(parts) - 1, int(k * len(parts) / max(1, len(beats))))]
        shot = _cam(b) or ("side" if action == "ride" else None) or _cam(cam_line) or None
        focus_obj = None
        if objs:
            named = [i for i, o in enumerate(objs) if (o["kind"] == "custom" and o.get("name", "") in t) or (any(world_has(t, w) for ws, kd in OBJECTS if kd == o["kind"] for w in ws) and o["kind"] != "bench")]
            if action == "ride":
                pass
            elif shot in ("closeup", "ecu", "dolly_in") or not people or any(w in t for w in ("close-up of", "zoom into", "zoom towards", "screen displays", "display", "highlight", "fine print", "clause")):
                focus_obj = named[0] if named else next((i for i, o in enumerate(objs) if o["kind"] != "bench"), None)
                if focus_obj is not None and shot is None:
                    shot = "ecu" if any(w in t for w in ("fine print", "clause", "highlight")) else "closeup"
        for o in objs:
            if o["kind"] == "document" and any(w in t for w in ("fine print", "clause", "highlight")) and o.get("text") and "hlLine" not in o:
                o["hlLine"] = len(o["text"]) - 1
        if q and objs and not any(o.get("text") for o in objs):
            objs.append({"kind": "computer", "text": q[:3]})
        steps.append({"text": b, "env": place, "tod": tod, "actors": [dict(p, dir=1 if j % 2 == 0 else -1) for j, p in enumerate(people)],
                      "acts": [action if j == 0 or action in ("chase", "walk", "sit", "look", "happy", "scared") else "idle" for j in range(len(people))],
                      "props": objs, "shot": shot, "focusObj": focus_obj, "focus": 0 if people else None,
                      "weather": sorted({v for ws, v in WEATHER if any(world_has(t, w) for w in ws)})})
        people_prev, objs_prev = people, objs
    return steps, place, tod


def world_has(t, w):
    return _has(t, w)


def _segments(tl):
    """Timeline lines -> engine segments: each Visual step gets its share of the line's time (at least ~0.9 s)."""
    segs, lines, k_shot = [], [], 0
    for i, s in enumerate(tl["segs"]):
        w = s["world"]; start = 0 if i == 0 else s["start"]; end = tl["segs"][i + 1]["start"] if i + 1 < len(tl["segs"]) else tl["total"]
        lines.append({"start": start, "words": s.get("words", [])})
        steps = w.get("steps") or [None]
        n = max(1, min(len(steps), int((end - start) / .9)))
        pick = [steps[int(j * len(steps) / n)] for j in range(n)]
        for j, st in enumerate(pick):
            base = {k: v for k, v in w.items() if k != "steps"}
            if st:
                base.update(st); base["acts"] = st["acts"]; base["speakerIdx"] = -1
            if not base.get("shot"):
                base["shot"] = "establishing" if (i == 0 and j == 0) else SHOT_CYCLE[k_shot % len(SHOT_CYCLE)]; k_shot += 1
            seg_start = start + (end - start) * j / n
            segs.append(dict(base, start=round(seg_start, 3), words=s.get("words", []) if j == 0 else [], key=f"{i}:{j}" if st else f"{w['scene']}",
                             scene=w["scene"], split=(n == 1 and (end - start) > 4.2)))
    return segs, lines


def render(sc, tl, d, g, size=(1080, 1920), fast=True):
    plan(sc, tl, g)
    eng = os.path.join(d, "world_engine"); shutil.rmtree(eng, ignore_errors=True)
    shutil.copytree(CINEMA / "engine", eng, ignore=shutil.ignore_patterns("scene.html"))
    fonts = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine" / "template" / "web" / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, os.path.join(eng, "fonts"), dirs_exist_ok=True)
    segs, lines = _segments(tl)
    print(f"  cinema: {len(segs)} shots for {len(lines)} spoken lines", flush=True)
    data = {"cfg": {"size": list(size), "fps": 30, "glScale": .7 if fast else 1, "hl": g.get("thumb_color", "#ffe34a")}, "segs": segs, "lines": lines, "total": tl["total"]}
    proj = os.path.join(d, "world"); os.makedirs(proj, exist_ok=True)
    json.dump(data, open(os.path.join(proj, "timeline.json"), "w"), indent=1)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"), CINEMA_PAGE="world.html", FFMPEG=FFMPEG)
    subprocess.run(["node", os.path.join(eng, "render.js"), proj], check=True, env=env)
    shutil.move(os.path.join(proj, "video.mp4"), os.path.join(d, "video.mp4"))


def preview(sc, tl, d, g, times=None, size=(1080, 1920)):
    """Quick stills for checking a plan: d/world/preview_<t>.jpg (default: the middle of every shot)."""
    plan(sc, tl, g)
    eng = os.path.join(d, "world_engine"); shutil.rmtree(eng, ignore_errors=True); shutil.copytree(CINEMA / "engine", eng)
    fonts = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine" / "template" / "web" / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, os.path.join(eng, "fonts"), dirs_exist_ok=True)
    segs, lines = _segments(tl)
    if times is None:
        times = [round((s["start"] + (segs[i + 1]["start"] if i + 1 < len(segs) else tl["total"])) / 2, 2) for i, s in enumerate(segs)]
    proj = os.path.join(d, "world"); os.makedirs(proj, exist_ok=True)
    json.dump({"cfg": {"size": list(size), "fps": 30, "glScale": .5, "hl": "#ffe34a"}, "segs": segs, "lines": lines, "total": tl["total"]}, open(os.path.join(proj, "timeline.json"), "w"), indent=1)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"), CINEMA_PAGE="world.html", FFMPEG=FFMPEG)
    subprocess.run(["node", os.path.join(eng, "render.js"), proj, "preview", *[str(t) for t in times]], check=True, env=env)
    return proj, segs
