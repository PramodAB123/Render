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


def parse(text):
    """-> list of scenes {title, visual, sfx, speech:[{speaker, say, tone}]} and a flat list of spoken lines."""
    t = str(text).replace("“", '"').replace("”", '"').replace("„", '"').replace("’", "'")
    t = re.sub(r"\(\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\)", " ", t)            # drop (00:00–00:10) timestamps
    t = re.sub(r"ACT\s+\d+\s*[–—-][^\n]*?(?=Scene\s+\d+)", " ", t, flags=re.I)  # drop ACT headings
    t = re.sub(r"ENDING TEXT:.*$", " ", t, flags=re.I | re.S)
    parts = re.split(r"(?=Scene\s+\d+\s*[–—-])", t, flags=re.I)
    scenes = []
    for chunk in parts:
        chunk = chunk.strip()
        if not chunk:
            continue
        hm = re.match(r"Scene\s+\d+\s*[–—-]\s*(.*?)(?=Visual:|Animation:|SFX:|Narrator:|Dialogue|$)", chunk, re.S | re.I)
        title = re.sub(r"\s+", " ", hm.group(1)).strip(" :") if hm else ""
        rest = chunk[hm.end():] if hm else chunk   # the heading is not part of anyone's name
        visual = " ".join(x for x in (_field(rest, "Visual"), _field(rest, "Animation")) if x)
        sfx = _field(rest, "SFX") or _field(rest, "Sound")
        speech = []
        body = re.sub(r"(Visual|Animation|SFX|Sound|Camera)\s*:\s*[^\"]*?(?=(Narrator|Narration|Dialogue)\b|[A-Z][\w ]{0,25}(?:\([^)]*\))?\s*:\s*\"|$)", " ", rest, flags=re.I)
        body = re.sub(r"Dialogue\s*[–—-]\s*", "", body, flags=re.I)
        for m in QUOTE.finditer(body):
            sp = re.sub(r"\s+", " ", m.group(1)).strip(); line = re.sub(r"\s+", " ", m.group(3)).strip()
            sp = " ".join(sp.split()[-2:]) if len(sp.split()) > 2 else sp   # e.g. 'Ghost Captain'
            if sp.lower() in ("visual", "animation", "sfx", "sound", "camera"):
                continue
            speech.append({"speaker": "narrator" if sp.lower() in ("narrator", "narration") else sp, "say": line, "tone": (m.group(2) or "").lower()})
        if speech or visual:
            scenes.append({"title": title, "visual": visual, "sfx": sfx, "speech": speech})
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
