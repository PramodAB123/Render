"""Design each stick character from what the script says about them: hat, clothes colours, extras (beard, eye patch,
glasses, cape, long hair), a prop in hand (sword, bow, lantern, map ...), build, and a ghost's glow colour.
Reads every sentence of the script that names the character (Visual / Animation lines, or the writer's 'look')."""
import re

COLOURS = {"black": "#2b2b33", "red": "#e0392f", "crimson": "#b3202a", "blue": "#2f63c9", "navy": "#2a3f8f", "green": "#3fa35b",
           "yellow": "#f2b52a", "gold": "#e6b422", "golden": "#e6b422", "purple": "#7a4bc4", "orange": "#ee7a22", "brown": "#7a4a2a",
           "white": "#eeeeee", "grey": "#8a9099", "gray": "#8a9099", "pink": "#e86fa0", "silver": "#b8c0c8"}
DEFAULT = ["#e0392f", "#f2b52a", "#2f63c9", "#3fa35b", "#7a4bc4", "#2a3f8f"]
HATS = [  # (words, costume) - first hit wins
    (("crown", "king", "queen", "prince", "princess"), "crown"), (("captain",), "captain"), (("sailor",), "sailor"),
    (("helmet", "soldier", "knight", "guard", "warrior", "viking"), "helmet"), (("wizard", "sorcerer", "mage", "witch"), "wizard"),
    (("hood", "hooded", "cloak", "thief", "assassin", "monk", "archer", "shadow"), "hood"), (("top hat", "gentleman", "magician"), "tophat"),
    (("cowboy", "sheriff", "ranger"), "cowboy"), (("turban",), "turban"), (("cap", "baseball", "blacksmith", "smith", "worker", "farmer"), "cap"),
    (("bandana", "pirate", "deckhand", "crew"), "bandana"), (("chef", "cook"), "chef"),
]
EXTRAS = [(("beard", "bearded", "old man", "grandpa", "dwarf"), "beard"), (("eye patch", "eyepatch", "one eye", "one-eyed"), "eyepatch"),
          (("glasses", "spectacles", "nerd", "scientist", "professor"), "glasses"), (("cape", "cloak", "king", "hero", "superhero"), "cape"),
          (("mustache", "moustache"), "mustache"), (("scar",), "scar"), (("long hair", "girl", "woman", "queen", "princess", "lady", "mother"), "hair")]
PROPS = [(("bow", "arrow", "archer"), "bow"), (("sword", "blade", "cutlass", "knight"), "sword"), (("lantern", "torch", "lamp"), "lantern"),
         (("staff", "wand", "wizard"), "staff"), (("treasure map", "map", "scroll"), "map"), (("spear", "trident"), "spear"),
         (("hammer", "blacksmith"), "hammer"), (("shield",), "shield"), (("phone",), "phone"), (("book",), "book")]
BIG = ("giant", "huge", "big", "fat", "tall", "strong", "muscular", "large")
SMALL = ("tiny", "small", "short", "little", "kid", "child", "boy", "young")


def _has(t, w):
    return re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) is not None


def about(name, text, others=()):
    """The script clauses that describe this character: clauses whose subject (a name in the first few words) is them,
    plus following 'he/she/his/her ...' clauses. Longer names win, so 'Captain' doesn't pick up what 'Ghost Captain' does."""
    me = name.lower(); full = {n.lower() for n in others} | {me}
    # a word that belongs to only one name works as a short name too ("Ghost" for "Ghost Captain")
    words = [w for n in full for w in n.split() if len(w) > 2 and w != n]
    alias = {w: n for n in full for w in n.split() if len(w) > 2 and w != n and words.count(w) == 1 and w not in full}
    names = sorted(full | set(alias), key=len, reverse=True)
    out, last, prev = [], None, None
    clauses = []
    for sent in re.split(r"[.!?;\n]+", str(text or "").lower()):   # the subject carries on within a sentence, not past it
        clauses.append(None)
        clauses += re.split(r",\s*(?:(?:and|while|then)\s+)?|\s+(?:while|as)\s+", sent)
    for cl in clauses:
        if cl is None:
            prev, last = last or prev, None; continue
        cl = cl.strip()
        if not cl:
            continue
        masked, subj = cl, None
        for n in names:   # longest first; blank each found name so shorter names can't match inside it
            m = re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", masked)
            if m:
                if m.start() <= 25 and (subj is None or m.start() < subj[1]):
                    subj = (alias.get(n, n), m.start())
                masked = masked[:m.start()] + "#" * len(n) + masked[m.end():]
        if subj:
            last = subj[0]
        elif re.match(r"(he|she|his|her|him)\b", cl):   # "He pulls out his bow" -> the last person named
            subj = (last or prev, 0); last = subj[0]
        elif masked == cl and last:   # no one else named in this sentence: same person
            subj = (last, 0)
        else:
            last = None
        if subj and subj[0] == me:
            out.append(re.sub(r"#+", "", masked))
    return ". ".join(out)


HOLD = r"(?:hold(?:s|ing)?|carr(?:y|ies|ying)|draws?|pulls? out|with|wield(?:s|ing)?|raises?|grabs?|swings?|his|her|their|a|an)\s+(?:[a-z]+\s+){0,2}"


def design(name, desc="", i=0, gender="male", role=""):
    t = f"{name} {role} {desc}".lower(); n = f"{name} {role}".lower()
    ghost = any(_has(n, w) for w in ("ghost", "spirit", "phantom", "spectre")) or any(w in t for w in ("ghostly", "transparent", "translucent"))
    costume = next((c for ws, c in HATS if any(_has(t, w) for w in ws)), "none")
    extras = sorted({e for ws, e in EXTRAS if any(_has(t, w) for w in ws)})
    if gender == "female" and "hair" not in extras:
        extras.append("hair")
    # a prop only when the character holds/uses it ("draws his sword", "pulls out his bow", "with a lantern"), or their role says so
    prop = next((p for ws, p in PROPS if any(re.search(HOLD + re.escape(w) + r"(?![a-z])", t) or _has(n, w) for w in ws)), None)
    # colours named on their clothes: "black coat", "red shirt" -> body colour, a second one for stripes
    cloth = r"[a-z]*(?:coat|shirt|hat|cloak|dress|jacket|bandana|vest|pants|robe|armou?r|suit|scarf|hoodie|tunic|uniform|clothes|outfit|cape)"
    named = [COLOURS[m] for m in re.findall(r"\b(" + "|".join(COLOURS) + r")(?:\s+[a-z]+)?\s+" + cloth, t)]
    if any(_has(n, c) for c in COLOURS):   # "Captain Black", "Red Riding Hood"
        named.insert(0, next(COLOURS[c] for c in COLOURS if _has(n, c)))
    main = named[0] if named else DEFAULT[i % len(DEFAULT)]
    stripe = named[1] if len(named) > 1 else ("#f6f1e8" if any(_has(t, w) for w in ("pirate", "sailor", "crew")) else main)
    # build words only count where they describe the person (near the start of their own clause: "Raju, a fat old farmer")
    person = (r"(?:\s+[a-z]+){0,2}\s+(?:man|woman|guy|girl|boy|kid|child|farmer|warrior|pirate|sailor|king|queen|knight|soldier|"
              r"giant|dwarf|person|figure|fellow|lady|hero|villain|captain|monster|beast|thief|chef|wizard|witch|robot)s?\b")
    size_of = lambda ws: any(re.search(r"\b" + w + person, t) for w in ws) or any(_has(n, w) for w in ws)
    size = 1.15 if size_of(BIG) else .85 if size_of(SMALL) else 1.0
    glow = "#ff5a4a" if ("red eyes" in t or "red glow" in t) else "#7ab8ff" if ("blue" in t and ghost) else "#8dffc0"
    return {"costume": costume, "cols": [main, stripe], "extras": extras, "prop": prop, "size": size, "ghost": ghost, "glow": glow,
            "vest": "#5a3a22" if any(_has(t, w) for w in ("coat", "vest", "jacket")) else None}
