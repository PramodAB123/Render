"""Screenplay-style custom scripts: ACT / Scene headings, Visual:, Animation:, SFX:, Narrator: "...", Dialogue - Name: "...".
Only the narrator and dialogue lines are spoken (in the order written). Visual/Animation text picks the scene,
time of day and mood for each spoken line; SFX notes become real sound effects. Any language works; Hindi and
other Devanagari text gets Hindi voices."""
import re

LABELS = r"(Visual|Animation|SFX|Sound|Music|Camera|Narrator|Narration|Dialogue|Ending text|Text)"
SCENE = re.compile(r"(?:ACT\s+\d+[^\n]*?(?=Scene\s+\d+)|)Scene\s+(\d+)\s*[–—-]?\s*([^\n(:]*?)\s*(?:\([^)]*\))?\s*(?=Visual:|Animation:|SFX:|Narrator:|Dialogue|$)", re.I)
QUOTE = re.compile(r'([A-Za-z][A-Za-z .\'-]{0,30}?)\s*(?:\(([^)]{1,20})\))?\s*:\s*"([^"]{1,400})"')
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def looks_like(text):
    t = str(text or "")
    return len(re.findall(r"\b(Scene\s+\d+|Visual:|Narrator:|Dialogue|SFX:|Animation:)", t, re.I)) >= 3


def _field(chunk, name):
    m = re.search(name + r"\s*:\s*(.*?)(?=" + LABELS + r"\s*[:–—-]|$)", chunk, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


BLOCK = r"(?:Visual|Animation|SFX|Sound|Music|Camera)"
STOP = r"(?=(?:Narrator|Narration|Dialogue|Visual|Animation|SFX|Sound|Music|Camera)\s*[:–—-]|\n\s*[A-Z][\w .'-]{0,25}(?:\([^)]*\))?\s*:\s*\"|$)"
JUNK = re.compile(r"^\s*(?:\S+\.(?:net|com|inc|live|media|tv|io|org|ai|co|app|gg|me|in)\S*|\d{1,3})\s*$", re.I)


def _beats(chunk, name):
    """A field's steps: '- bullet' lines (sub-bullets join their parent) or sentences."""
    m = re.search(r"\b" + name + r"\s*:\s*(.*?)" + STOP, chunk, re.S | re.I)
    if not m:
        return []
    raw = m.group(1); out = []
    if re.search(r"^\s*[-•*]\s+", raw, re.M):
        for ln in raw.split("\n"):
            b = re.match(r"^(\s*)[-•*]\s+(.*)", ln)
            if b and len(b.group(1)) >= 2 and out:
                out[-1] += " " + b.group(2).strip()          # nested bullet -> part of the step above
            elif b:
                out.append(b.group(2).strip())
            elif ln.strip() and out:
                out[-1] += " " + ln.strip()
    else:
        out = [x.strip() for x in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", raw)) if x.strip()]
    return [re.sub(r"\s+", " ", x) for x in out if x]


def parse(text):
    """-> list of scenes {title, visual, beats, camera, sfx, music, speech:[{speaker, say, tone}]} and a flat list of spoken lines.
    Only Narrator / Dialogue lines are spoken; quotes inside Visual / Camera / Music / SFX steps (screen text, signs) are not."""
    t = str(text).replace("“", '"').replace("”", '"').replace("„", '"').replace("’", "'").replace("&#34;", '"').replace("&#39;", "'").replace("&quot;", '"')
    t = "\n".join(ln for ln in t.split("\n") if not JUNK.match(ln))                  # pasted website names, stray numbers
    t = re.sub(r"\(\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\)", " ", t)            # drop (00:00–00:10) timestamps
    t = re.sub(r"ACT\s+\d+\s*[–—-][^\n]*?(?=Scene\s+\d+)", " ", t, flags=re.I)  # drop ACT headings
    t = re.sub(r"ENDING TEXT:.*$", " ", t, flags=re.I | re.S)
    parts = re.split(r"(?=Scene\s+\d+\s*[–—-])", t, flags=re.I)
    scenes = []
    for chunk in parts:
        chunk = chunk.strip()
        if not chunk:
            continue
        hm = re.match(r"Scene\s+\d+\s*[–—-]\s*(.*?)(?=\n|Visual:|Animation:|SFX:|Narrator:|Dialogue|$)", chunk, re.S | re.I)
        title = re.sub(r"\s+", " ", hm.group(1)).strip(" :") if hm else ""
        rest = chunk[hm.end():] if hm else chunk   # the heading is not part of anyone's name
        beats = _beats(rest, "Visual") + _beats(rest, "Animation")
        visual = " ".join(beats)
        camera = _beats(rest, "Camera")
        sfx = _field(rest, "SFX") or _field(rest, "Sound"); music = _field(rest, "Music")
        speech = []
        body = re.sub(r"\b" + BLOCK + r"\s*:.*?" + STOP, " ", rest, flags=re.S | re.I)   # drop the non-spoken blocks entirely
        body = re.sub(r"Dialogue\s*[–—-]\s*", "", body, flags=re.I)
        for m in QUOTE.finditer(body):
            sp = re.sub(r"\s+", " ", m.group(1)).strip(); line = re.sub(r"\s+", " ", m.group(3)).strip()
            sp = " ".join(sp.split()[-2:]) if len(sp.split()) > 2 else sp   # e.g. 'Ghost Captain'
            if sp.lower() in ("visual", "animation", "sfx", "sound", "camera", "music"):
                continue
            speech.append({"speaker": "narrator" if sp.lower() in ("narrator", "narration") else sp, "say": line, "tone": (m.group(2) or "").lower()})
        if speech or visual:
            scenes.append({"title": title, "visual": visual, "beats": beats, "camera": camera, "sfx": sfx, "music": music, "speech": speech})
    lines = [dict(s, scene=k) for k, sc in enumerate(scenes) for s in sc["speech"]]
    return scenes, lines


def is_hindi(lines):
    txt = " ".join(l["say"] for l in lines)
    return len(DEVANAGARI.findall(txt)) > len(txt) * 0.2


# ---------------- scene direction from the Visual / Animation text (stick mode) ----------------
RULES = [  # (keywords, setup, time of day)
    (("storm", "lightning", "thunder", "huge waves", "rain"), "storm", "night"),
    (("treasure map", " map", "red x", "glowing x"), "treasuremap", None),
    (("ghost", "spirit", "phantom", "green smoke"), "ghost", "night"),
    (("skeleton", "bones", "undead"), "skeletons", "night"),
    (("temple", "stone door", "skull symbol", "ruins", "ancient"), "temple", "dusk"),
    (("tentacle", "monster", "attack", "fight", "battle", "clash", "strike", "explodes", "trap", "spikes", "blade"), "impact", None),
    (("jungle", "forest", "trees", "swamp"), "jungle", "dusk"),
    (("treasure chest", "chest", "gold", "diamond", "coins"), "reveal", None),
    (("ship", "ocean", "sea", "sailing", "boat", "island"), "sea", None),
    (("king", "queen", "throne"), "throne", None), (("blacksmith", "forge"), "forge", None),
    (("army", "armies", "soldiers"), "armies", None), (("castle", "kingdom"), "kingdoms", "dusk"),
    (("celebrate", "jumps", "excited", "party", "crew looks"), "crowd", None),
    (("run", "chase", "charges", "flee"), "run", None), (("walk", "enter"), "walk", "dusk"),
    (("blueprint", "plan", "diagram"), "blueprint", None), (("dark", "night"), "night", "night"),
]
LABEL = {"impact": "CLANG", "reveal": "GOLD", "treasuremap": "X", "storm": "", "temple": "", "blueprint": "THE PLAN"}


def direct(scene):
    v = (scene["title"] + " " + scene["visual"]).lower().replace("storm disappears", "").replace("storm clears", "")
    for keys, setup, tod in RULES:
        if any(k in v for k in keys):
            return setup, tod or ("night" if "dark" in v else "day")
    return None, "night" if "dark" in v else "day"


def mood(line, setup):
    s, t = line["say"], line.get("tone", "")
    if line["speaker"].lower().startswith("ghost"):
        return "angry"
    if "whisper" in t:
        return "scared"
    if any(w in s.lower() for w in ("help", "बचाओ", "डर", "scared", "run")):
        return "scared"
    if "!" in s and setup in ("impact", "storm", "ghost", "skeletons"):
        return "shocked"
    if any(w in s for w in ("वाह", "हा हा", "haha", "wow")) or setup in ("reveal", "crowd"):
        return "happy"
    if s.rstrip().endswith("?"):
        return "think"
    return "calm" if line["speaker"] == "narrator" else ("shocked" if "!" in s else "smug")


SFX_HINTS = {"wave": "water", "ocean": "water", "wind": "wind", "creak": "creak", "thunder": "boom", "rain": "rain", "lightning": "boom",
             "sword": "clink", "clash": "clink", "slash": "whoosh", "roar": "boom", "monster": "boom", "bones": "clink", "laugh": "chime",
             "chime": "chime", "sparkle": "chime", "magic": "chime", "coin": "chime", "footstep": "steps", "explosion": "boom", "blast": "boom",
             "impact": "boom", "scream": "whoosh", "whisper": "wind", "insect": "wind", "jungle": "wind", "stone": "boom", "rumble": "boom",
             "click": "clink", "blade": "whoosh", "arrow": "whoosh", "crack": "clink", "fire": "fire", "jump": "pop", "splash": "water"}


def sfx_tags(text):
    t = str(text or "").lower()
    return sorted({v for k, v in SFX_HINTS.items() if k in t})


# ---------------- accurate pictures + animation cues from the Visual / Animation text ('ai' mode) ----------------
PLACES = [  # (keywords, what the background must show) - most specific first; scenes with no place keep the last one
    (("storm", "huge waves", "lightning"), "a pirate ship in a violent storm at sea, huge dark waves, lightning, heavy rain"),
    (("treasure map", "wooden table", "cabin"), "a captain's cabin on a ship, an old treasure map spread on a wooden table, candle light"),
    (("trap", "spikes", "pressure plate", "blades"), "inside an ancient temple corridor, stone floor tiles, spikes and swinging blades, red warning glow"),
    (("temple", "stone door", "skull symbol"), "an ancient stone temple entrance, giant carved stone door with a skull symbol, glowing writings"),
    (("treasure chest", "golden platform"), "a treasure chamber, a huge treasure chest on a golden platform, piles of gold coins and diamonds, light rays"),
    (("swamp",), "a murky jungle swamp, twisted roots, green mist"),
    (("jungle", "forest", "trees"), "a dark dense jungle path, giant leaves, vines, mist"),
    (("island", "shore", "beach"), "a mysterious tropical island rising out of fog, mountains and jungle, calm sea"),
    (("deck", "ship", "sailing", "boat"), "the wooden deck of an old pirate ship at sea, sails and ropes, ocean horizon"),
    (("graveyard", "cemetery", "grave"), "a foggy graveyard at night, crooked tombstones, dead trees, full moon"),
    (("throne", "castle", "kingdom"), "a grand medieval castle hall, stone pillars, banners, a throne"),
    (("battlefield", "armies"), "a wide medieval battlefield, banners, smoke, distant castle"),
    (("forge", "blacksmith"), "a blacksmith forge, glowing fire, anvil, hammers"),
    (("bedroom", "hallway", "kitchen", "house", "living room"), "inside an old house, a dim hallway, wooden floor, a window"),
    (("street", "city", "town"), "an old town street, houses, lamps"),
    (("space", "planet", "galaxy"), "deep space, a giant planet, stars and a glowing nebula"),
    (("laboratory", "lab "), "a science laboratory, glowing screens, glass tubes"),
    (("desert",), "a vast desert, sand dunes, blazing sun"), (("mountain",), "dramatic mountains, cliffs, clouds"),
    (("sea", "ocean", "waves"), "an open ocean, rolling waves, wide sky"),
]
LIGHT = [(("night", "dark", "moon"), "night, moonlight, deep blue shadows"), (("dawn", "sunrise"), "sunrise, warm golden light"),
         (("sunset", "dusk"), "sunset, orange sky"), (("green smoke", "ghost"), "eerie green glow, smoke"),
         (("fire", "flames"), "orange firelight"), (("blue light",), "mysterious blue light"), (("golden", "gold"), "golden glow")]
PROPS = ["treasure map", "red x", "treasure chest", "gold coins", "diamonds", "skull", "sword", "crystal", "lantern", "candle", "rope",
         "cannon", "anchor", "coconut", "tentacle", "bones", "stone door", "spikes", "blades", "fog", "lightning", "rain", "fire"]


def place_prompt(scene, prev=None, names=()):
    """A short picture prompt the image model follows: WHERE first, then light, then key props (it reads ~70 words max).
    People are drawn by the animation, so names and actions are left out of the picture."""
    v = (scene.get("title", "") + " " + scene.get("visual", "")).lower().replace("storm disappears", "clear sky").replace("storm clears", "clear sky")
    for n in names:
        v = v.replace(n.lower(), "")
    # a daydream ("imagining", "thought bubble") or a crowd of skeletons doesn't move the scene somewhere new
    v_place = re.split(r"imagin|thought bubble|dream", v)[0]
    hits = [(min(v_place.find(k) for k in keys if k in v_place), i, p) for i, (keys, p) in enumerate(PLACES) if any(k in v_place for k in keys)]
    place = (min(hits)[2] if hits else None) or prev or "a wide cinematic landscape"   # the place the scene mentions first
    light = [l for keys, l in LIGHT if any(k in v for k in keys)][:2]
    props = [p for p in PROPS if p in v and p not in place][:4]
    return ", ".join([place] + light + props), place


FX = [  # Animation/Visual words -> effects drawn on top of the picture
    (("rain",), "rain"), (("lightning", "thunder"), "lightning"), (("shake", "tilts", "explosion", "explodes", "impact", "rumble"), "shake"),
    (("zoom",), "zoom"), (("fog", "mist"), "fog"), (("glowing eyes", "eyes blink", "eyes appear"), "eyes"),
    (("sparkle", "particles", "glow", "magical", "light rays"), "sparkle"), (("coins",), "coins"), (("fire", "flames"), "fire"),
    (("green smoke", "smoke"), "smoke"), (("tilts", "rocking", "waves hit"), "tilt"), (("jump", "jumps"), "jump"),
    (("sword", "clash", "slash", "strike", "fight", "attack"), "clash"), (("explosion", "explodes", "shatter", "blast"), "boom"),
    (("dust", "stones move"), "dust"), (("pan", "pans"), "pan"), (("slow motion", "slow-motion"), "slowmo"),
    (("thought bubble", "imagining"), "bubble"), (("arrow",), "arrow"), (("walk", "walking"), "walk"), (("run", "running", "charges"), "run"),
]


def fx_tags(text):
    t = str(text or "").lower()
    return sorted({f for keys, f in FX if any(k in t for k in keys)})


# ---------------- music for each scene, read from the script (Music:/SFX: notes, then the scene's own words) ----------------
FEELS = [  # checked in order; first hit wins
    ("horror", ("horror sting", "villain", "ghost", "scream", "eerie", "spooky", "curse", "creepy", "haunted", "dead", "skull", "green smoke", "भूत")),
    ("action", ("battle", "fight", "clash", "attack", "sword", "charges", "monster", "explosion", "explodes", "strike", "chase", "storm", "lightning", "trap")),
    ("tense", ("dark", "whisper", "footsteps", "mysterious", "glowing eyes", "shadow", "danger", "suspense", "sneak", "night", "fog")),
    ("magic", ("magical", "sparkle", "glow", "treasure", "gold", "crystal", "reveal", "chime", "diamond", "wonder")),
    ("sad", ("sad", "cry", "tears", "lonely", "loss", "funeral", "goodbye", "rain alone")),
    ("epic", ("epic", "cinematic", "hero", "victory", "army", "kingdom", "mountain", "sunrise", "triumph")),
    ("playful", ("happy", "funny", "comedic", "cartoon", "laugh", "celebrate", "jump", "excited", "silly", "party", "coins")),
]


def music_feel(scene_or_text):
    """The script decides the music: an explicit Music:/SFX: note wins, then what the scene shows."""
    if isinstance(scene_or_text, dict):
        notes = (scene_or_text.get("music", "") + " " + scene_or_text.get("sfx", "")).lower()
        body = (scene_or_text.get("title", "") + " " + scene_or_text.get("visual", "")).lower()
    else:
        notes, body = "", str(scene_or_text or "").lower()
    for text in (notes, body):
        # "happy music switches to horror sting": the LAST feel named is where the scene ends up
        hits = [(max(text.rfind(k) for k in keys), name) for name, keys in FEELS if any(k in text for k in keys)]
        if hits:
            return max(hits)[1]
    return None


def _has(text, k):
    return re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", text) is not None


def music_feel(scene_or_text):   # noqa: F811  (replaces the version above)
    """The script decides the music: an explicit Music:/SFX: note wins, then what the scene shows.
    Feels are checked in FEELS order (horror > action > tense > ...); "X switches to Y" ends on Y."""
    if isinstance(scene_or_text, dict):
        notes = (scene_or_text.get("music", "") + " " + scene_or_text.get("sfx", "")).lower()
        body = (scene_or_text.get("title", "") + " " + scene_or_text.get("visual", "")).lower()
    else:
        notes, body = "", str(scene_or_text or "").lower()
    for text in (notes, body):
        m = re.search(r"(?:switch(?:es)?|turns?|changes?) (?:in)?to (.*)", text)
        if m:
            text = m.group(1)
        for name, keys in FEELS:
            if any(_has(text, k) for k in keys):
                return name
    return None
