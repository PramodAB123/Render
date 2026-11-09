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
    (("underwater", "under the sea", "coral", "reef", "seabed"), "underwater"), (("beach", "shore", "coast"), "beach"), (("ship", "deck", "boat", "जहाज"), "ship"),
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
TOD = [(("night", "midnight", "moon", "dark", "रात"), "night"), (("sunset", "dusk", "evening", "शाम"), "dusk"), (("dawn", "sunrise", "morning", "सुबह"), "dawn")]
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
    for i, c in enumerate(cast):
        nm = str(c.get("name", "")); ty = next((ACTORS[w] for w in sorted(ACTORS, key=len, reverse=True) if _has(nm.lower(), w)), None)
        roster.append({"name": nm, "type": ty or ("ghost" if c.get("ghost") else "person"), **{k: c.get(k) for k in ("cols", "costume", "extras", "prop", "size", "ghost", "glow")},
                       "female": c.get("gender") == "female"})
    for ty in _actors_in(everything):
        if ty not in [r["type"] for r in roster]:
            roster.append({"name": ty, "type": ty})
    if not roster:
        roster = [{"name": "narrator", "type": "person", "cols": ["#2f63c9", "#2f63c9"]}]
    habitat = next((HOME[r["type"]] for r in roster if r["type"] in HOME), None)
    env, tod, scene_no, shot_k, prev_scene = habitat or "savanna", "day", -1, 0, None
    prev_cast = [0]
    for i, (ln, sg) in enumerate(zip(lines, segs)):
        vis = str(ln.get("scene_visual") or ln.get("image") or "").lower(); say = str(ln.get("say", "")).lower(); t = vis + " " + say
        sid = ln.get("scene", i if not vis else vis[:60])
        new_scene = sid != prev_scene; prev_scene = sid
        if new_scene:
            env = _first(vis, PLACES) or _first(say, PLACES) or env
            tod = _first(vis, TOD) or ("night" if env in ("space", "moon", "graveyard") else "day" if scene_no < 0 else tod)
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
        here = here[:4] or prev_cast; prev_cast = here
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
        sg["world"] = {"scene": scene_no, "env": env, "tod": tod, "weather": weather, "seed": 11 + scene_no * 7,
                       "actors": [dict(roster[k], dir=1 if j % 2 == 0 else -1) for j, k in enumerate(here)], "acts": acts,
                       "speakerIdx": next((j for j, k in enumerate(here) if spk and roster[k]["name"].lower() == spk), -1),
                       "shot": shot, "shot2": nxt, "action": action, "fx": ln.get("fx") or [], "focus": None if shot in ("two_shot", "establishing", "aerial") else
                       next((j for j, k in enumerate(here) if spk and roster[k]["name"].lower() == spk), 0)}
    summary = ", ".join(f"{r['name']} ({r['type']})" for r in roster)
    print(f"  cinema world: cast {summary}; places " + " > ".join(dict.fromkeys(s["world"]["env"] for s in segs)), flush=True)
    return roster


def render(sc, tl, d, g, size=(1080, 1920), fast=True):
    plan(sc, tl, g)
    eng = os.path.join(d, "world_engine"); shutil.rmtree(eng, ignore_errors=True)
    shutil.copytree(CINEMA / "engine", eng, ignore=shutil.ignore_patterns("scene.html"))
    fonts = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine" / "template" / "web" / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, os.path.join(eng, "fonts"), dirs_exist_ok=True)
    segs = []
    for i, s in enumerate(tl["segs"]):
        w = s["world"]; start = 0 if i == 0 else s["start"]; nxt = tl["segs"][i + 1]["start"] if i + 1 < len(tl["segs"]) else tl["total"]
        segs.append(dict(w, start=start, words=s.get("words", []), scene=w["scene"], split=(nxt - start) > 4.2))
    data = {"cfg": {"size": list(size), "fps": 30, "glScale": .7 if fast else 1, "hl": g.get("thumb_color", "#ffe34a")}, "segs": segs, "total": tl["total"]}
    json.dump(data, open(os.path.join(d, "timeline_world.json"), "w"), indent=1)
    # render.js reads <project>/timeline.json: give it the world timeline in a sub-project folder
    proj = os.path.join(d, "world"); os.makedirs(proj, exist_ok=True)
    shutil.copy(os.path.join(d, "timeline_world.json"), os.path.join(proj, "timeline.json"))
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"), CINEMA_PAGE="world.html", FFMPEG=FFMPEG)
    subprocess.run(["node", os.path.join(eng, "render.js"), proj], check=True, env=env)
    shutil.move(os.path.join(proj, "video.mp4"), os.path.join(d, "video.mp4"))


def preview(sc, tl, d, g, times, size=(1080, 1920)):
    """Quick stills for checking a plan: d/world/preview_<t>.jpg."""
    plan(sc, tl, g)
    eng = os.path.join(d, "world_engine"); shutil.rmtree(eng, ignore_errors=True); shutil.copytree(CINEMA / "engine", eng)
    fonts = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine" / "template" / "web" / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, os.path.join(eng, "fonts"), dirs_exist_ok=True)
    segs = []
    for i, s in enumerate(tl["segs"]):
        w = s["world"]; start = 0 if i == 0 else s["start"]; nxt = tl["segs"][i + 1]["start"] if i + 1 < len(tl["segs"]) else tl["total"]
        segs.append(dict(w, start=start, words=s.get("words", []), scene=w["scene"], split=(nxt - start) > 4.2))
    proj = os.path.join(d, "world"); os.makedirs(proj, exist_ok=True)
    json.dump({"cfg": {"size": list(size), "fps": 30, "glScale": .5, "hl": "#ffe34a"}, "segs": segs, "total": tl["total"]}, open(os.path.join(proj, "timeline.json"), "w"))
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"), CINEMA_PAGE="world.html", FFMPEG=FFMPEG)
    subprocess.run(["node", os.path.join(eng, "render.js"), proj, "preview", *[str(t) for t in times]], check=True, env=env)
    return proj
