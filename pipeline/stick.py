"""stick mode: a stick-figure explainer/story made with the stick-figure engine of claude-animation-skills
(MIT, Artem Novitckii; checked out by the workflow into vendor/animation-skills). The engine's rig, props,
whip transitions, 1-2 word lowercase Poppins captions and grade are used as they are; stick/auto_shots.js
turns our story timeline into its shot list automatically."""
import design  # noqa: E402
import json, os, re, shutil, subprocess
import requests
from common import load_config, ROOT, FFMPEG

ENGINE = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine"
SETUPS = ["closeup", "talk", "walk", "run", "crowd", "object", "reveal", "night", "impact", "sea", "bigtext", "think",
          "kingdoms", "armies", "forge", "throne", "blueprint", "bridge", "messenger",
          "storm", "treasuremap", "jungle", "skeletons", "temple", "ghost"]
COSTUMES = ["none", "crown", "helmet", "hood", "wizard", "cap", "bandana", "sailor", "captain"]
MOODS = ["calm", "happy", "scared", "shocked", "angry", "sad", "smug", "dizzy", "think"]
COLS = ["red", "blue", "yellow", "green", "navy", "purple"]
# explainer genres follow the stick-figure skill; story genres follow a hook -> escalation -> twist -> cliffhanger arc
EXPLAIN = ("a hook that starts in action, the common belief, a turn on \"But\", examples that build, one shot that shows how it works, "
           "and a payoff that answers the hook.")
STORY = ("a hook already in motion, who and where in one line, three escalations that each make things worse with a concrete detail, "
         "a twist two thirds in that changes everything, and a cliffhanger ending.")
# the reference Short ("An Unstoppable Spear vs an Unbreakable Shield"): a paradox or what-if told as a fable
FABLE = ("open on the paradox or what-if as a question, set up two sides or rivals and what each one claims, someone tests it "
         "with a concrete plan, the stakes escalate (armies, a king, a deadline), a clever twist resolves it in a way nobody expected, "
         "and a final punchline line.")
STRUCTURE = {"science": EXPLAIN, "motivation": EXPLAIN, "comedy": FABLE, "history": FABLE, "mystery": FABLE, "horror": STORY, "adventure": STORY, "story": FABLE}

PROMPT = """You write a {seconds}-second vertical stick-figure cartoon video. Genre: {genre}. Style: {tone}
Make ONE completely original story or explainer (never copy existing videos). Idea: {idea}
{inspo}
Structure: {structure} One idea per line, 6-14 words.
Narrated like a storyteller: calm, clear, a little wry, short sentences; characters may say a line themselves ("speaker").
For every line choose a "setup" (what we see): closeup (big face reacting), talk (two characters), walk, run, crowd,
object (a crate labelled with "label"), reveal (a chest opens; "label" pops out), night (dark, lantern, scared),
impact (comic burst with "label" like BOOM), sea (ship on the sea), bigtext ("label" in huge letters), think (question marks),
kingdoms (two castles and armies at dusk), armies (two armies charging, seen from above), forge (blacksmith at the fire),
throne (a king in the throne room), blueprint (a plan drawn on blue paper; "label" = its title, "hl" = a stamp word),
bridge (two characters meet on a stone bridge), messenger (someone running with a scroll).
Change the setup every line. "mood" is one of: {moods}. "time_of_day": day, dusk, night or dawn.
"ground": grass, sand, snow, road, floor or sea.
Reply with JSON only:
{{"title": "under 60 chars", "description": "2 sentences", "tags": ["5-8 tags"], "thumb_text": "2-4 WORDS",
  "characters": [{{"name": "...", "role": "e.g. blacksmith, king, messenger", "gender": "male|female", "color": "red|blue|yellow|green|navy|purple",
                    "costume": "none|crown|helmet|hood|wizard|cap|bandana|sailor|captain",
                    "look": "one sentence: clothes and their colours, hat, beard/glasses/eye patch, what they carry, build"}}],
  "lines": [{{"say": "...", "speaker": "narrator or a character name", "setup": "closeup", "mood": "calm", "who": 0, "label": "",
              "time_of_day": "day", "ground": "grass", "hl": "KEYWORD",
              "image": "one vivid sentence describing the illustrated background of this moment: place, objects, light (no people)"}}]}}
"who" is the index of the character on screen. Write about {lines} lines. The last line ends with: "{cta}" """

MORE = """Continue this {genre} stick-figure video with about {lines} more lines in the same JSON line format
(say, speaker, setup, mood, who, label, time_of_day, ground, hl, image), building toward the payoff. Last lines so far: {last}
Reply with JSON only: {{"lines": [...]}}"""


def _ollama(prompt, n=2500):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt,
                      "format": "json", "stream": False, "options": {"temperature": 0.85, "num_ctx": 4096, "num_predict": n}}, timeout=1500)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def _pick(v, allowed, default):
    v = str(v or "").lower().strip()
    return v if v in allowed else next((a for a in allowed if a in v), default)


def write_story(g, idea, inspo, secs):
    want = secs * 2.75; n_lines = max(8, round(want / 10))
    ins = ("Trending titles (tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
    story = None
    for attempt in range(3):
        try:
            story = _ollama(PROMPT.format(seconds=secs, genre=g["name"], tone=g["tone"], idea=idea, inspo=ins, moods=", ".join(MOODS),
                                          structure=STRUCTURE.get(g["name"], STRUCTURE["story"]),
                                          lines=min(n_lines, 16), cta=g["cta"]))
            if story.get("lines"):
                break
        except Exception as e:
            print(f"  stick story retry ({e})")
    if not story or not story.get("lines"):
        raise SystemExit("The stick-figure story writer (Ollama) failed. Nothing was uploaded. Please run again.")
    raw = [l for l in story["lines"] if isinstance(l, dict) and l.get("say")]
    for attempt in range(6):
        if sum(len(str(l["say"]).split()) for l in raw) >= want * 0.85:
            break
        try:
            more = [l for l in _ollama(MORE.format(genre=g["name"], lines=10, last=" ".join(str(l["say"]) for l in raw[-4:])), 1800).get("lines", [])
                    if isinstance(l, dict) and l.get("say")]
            if not more:
                break
            raw += more
        except Exception as e:
            print(f"  stick continue retry ({e})")
    chars = [c for c in story.get("characters", []) if isinstance(c, dict)][:4] or [{"name": "Sam", "color": "red", "hat": "bandana"}]
    lines, prev = [], None
    for i, l in enumerate(raw):
        setup = _pick(l.get("setup"), SETUPS, "talk")
        if setup == prev:   # never the same setup twice in a row
            setup = SETUPS[(SETUPS.index(setup) + 3) % len(SETUPS)]
        prev = setup
        try:
            who = int(l.get("who") or 0) % len(chars)
        except (TypeError, ValueError):
            who = 0
        lines.append({"say": str(l["say"]).strip(), "speaker": str(l.get("speaker") or "narrator"), "setup": setup,
                      "mood": _pick(l.get("mood"), MOODS, "calm"), "who": who,
                      "label": str(l.get("label") or "")[:16], "tod": _pick(l.get("time_of_day"), ["day", "dusk", "night", "dawn"], "day"),
                      "ground": _pick(l.get("ground"), ["grass", "sand", "snow", "road", "floor", "sea"], "grass"),
                      "hl": str(l.get("hl") or "").upper()[:16], "image": str(l.get("image") or "")[:300]})
    if g["cta"].lower().rstrip(".") not in lines[-1]["say"].lower():
        lines.append({"say": g["cta"], "setup": "bigtext", "mood": "happy", "who": 0, "label": g["cta"].split()[0], "tod": "day", "ground": "grass", "hl": ""})
    # genre conditions: dark genres stay at night/dusk, with scared moods and the lantern scene, whatever the LLM picked
    # history keeps the warm storybook light of the reference Short (dusk, dawn, a little day)
    dark = {"horror": ("night", "dusk"), "mystery": ("night", "dusk", "dawn"), "history": ("dusk", "dawn", "day")}.get(g["name"])
    if dark:
        for k, ln in enumerate(lines):
            if ln["tod"] not in dark:
                ln["tod"] = dark[k % len(dark)] if g["name"] != "horror" else "night"
            if g["name"] == "horror" and ln["mood"] in ("calm", "happy") and ln["setup"] != "bigtext":
                ln["mood"] = "scared" if k % 2 else "shocked"
            if g["name"] == "horror" and ln["setup"] in ("sea", "crowd") and k % 2:
                ln["setup"] = "night"
    lines[0]["setup"] = "closeup" if lines[0]["setup"] not in ("closeup", "impact", "run") else lines[0]["setup"]
    cast = []
    for i, c in enumerate(chars):
        col = _pick(c.get("color"), COLS, COLS[i % len(COLS)])
        costume = _pick(c.get("costume") or c.get("hat"), COSTUMES, "none")
        role = str(c.get("role") or "").lower()
        if costume == "none":   # dress characters for their role (king -> crown, soldier -> helmet ...)
            costume = next((v for k, v in (("king", "crown"), ("queen", "crown"), ("soldier", "helmet"), ("knight", "helmet"), ("guard", "helmet"),
                                           ("wizard", "wizard"), ("monk", "hood"), ("thief", "hood"), ("smith", "cap"), ("pirate", "bandana"),
                                           ("sailor", "sailor"), ("captain", "captain")) if k in role), "none")
        gen = _pick(c.get("gender"), ["male", "female"], "male"); nm = str(c.get("name") or f"Hero{i}")
        lk = design.design(nm, str(c.get("look") or ""), i, gen, role)
        if costume == "none":
            costume = lk["costume"]
        cast.append({"name": nm, "col": col, "costume": costume, "gender": gen, **{k: v for k, v in lk.items() if k != "costume"}})
        if c.get("color") in COLS and not c.get("look"):
            cast[-1]["cols"] = None   # keep the engine palette the writer picked
    # voices: storyteller narrator (genre voice, a touch slower); each character speaks with its own free Edge voice and mood
    from toon import VOICES, MOOD
    used = {g.get("voice", {}).get("edge_voice")}; vmap = {}
    for c in cast:
        opts = [v for v in VOICES[(c["gender"], "adult")] if v not in used] or VOICES[(c["gender"], "adult")]
        vmap[c["name"].lower()] = opts[0]; used.add(opts[0])
    for ln in lines:
        ln.setdefault("speaker", "narrator")
        v = vmap.get(ln["speaker"].lower())
        if v:
            ln["voice"], (ln["rate"], ln["pitch"]) = v, MOOD.get(ln["mood"], MOOD["calm"])
            ln["who"] = next((k for k, c in enumerate(cast) if c["name"].lower() == ln["speaker"].lower()), ln["who"])
        else:
            ln["rate"] = {"scared": "+4%", "shocked": "+2%", "sad": "-8%"}.get(ln["mood"], "-4%")
    skill_voice(lines, cast)
    print(f"  stick story: {story.get('title')!r}, {len(lines)} lines, cast: {', '.join(c['name'] for c in cast)}")
    return {"title": str(story.get("title") or idea)[:70], "description": str(story.get("description") or idea),
            "tags": [str(t) for t in story.get("tags", [])][:10], "thumb_text": str(story.get("thumb_text") or "WHAT IF")[:24],
            "lines": lines, "cast": cast}


HINDI_VOICES = {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"}
# the skill's free Kokoro narrator and some distinct character voices
KOKORO = {"narrator": "am_michael", "male": ["am_adam", "bm_george", "bm_lewis", "am_eric"], "female": ["af_heart", "bf_emma", "af_bella", "af_nicole"]}
KSPEED = {"calm": 1.12, "happy": 1.16, "scared": 1.2, "shocked": 1.18, "angry": 1.1, "sad": 1.0, "smug": 1.1, "dizzy": 1.05, "think": 1.06}


def skill_voice(lines, cast):
    """English stick videos use the skill's Kokoro voices and its near-gapless pacing: 0.12 s between lines,
    a beat more after the hook and after questions/exclamations (tts_kokoro.py)."""
    hindi = any(re.search(r"[\u0900-\u097F]", l["say"]) for l in lines)
    kv, used = {}, set()
    for k, c in enumerate(cast):
        opts = [v for v in KOKORO[c.get("gender", "male")] if v not in used]; kv[c["name"].lower()] = (opts or KOKORO[c.get("gender", "male")])[0]; used.add(kv[c["name"].lower()])
    for i, ln in enumerate(lines):
        ln["gap_after"] = 0.24 if (i == 0 or ln["say"].rstrip().endswith(("?", "!"))) else 0.12
        if hindi:
            continue
        ln["engine"] = "kokoro"; ln["kvoice"] = kv.get(str(ln.get("speaker", "")).lower(), KOKORO["narrator"])
        ln["kspeed"] = 1.12 if ln["kvoice"] == KOKORO["narrator"] else KSPEED.get(ln.get("mood"), 1.12)
        if any(c.get("ghost") and c["name"].lower() == str(ln.get("speaker", "")).lower() for c in cast):
            ln["kspeed"] = 0.92
    return lines


def from_screenplay(g, text):
    """Your own screenplay -> stick story without the LLM: only Narrator/Dialogue lines are spoken, the Visual/Animation
    notes pick each line's scene, the SFX notes become sound effects, and every character gets a costume and voice."""
    import screenplay as sp
    scenes, spoken = sp.parse(text)
    if not spoken:
        raise SystemExit("The screenplay has no Narrator or Dialogue lines in quotes, so there is nothing to say.")
    hindi = sp.is_hindi(spoken)
    names = []
    for l in spoken:
        if l["speaker"] != "narrator" and l["speaker"] not in names:
            names.append(l["speaker"])
    cast = []
    for i, n in enumerate(names or ["Hero"]):
        low = n.lower(); ghost = "ghost" in low or "spirit" in low
        desc = design.about(n, '. '.join(x['visual'] for x in scenes), names)
        gender = "female" if any(w in (low + " " + desc.lower()) for w in ("queen", "girl", "woman", "mother", "lady", "princess", " she ", " her ")) else "male"
        lk = design.design(n, desc, i, gender)
        costume = lk["costume"] if lk["costume"] != "none" else "bandana"
        cast.append({"name": n, "col": ["red", "yellow", "blue", "green", "purple", "navy"][i % 6], "gender": gender,
                     **lk, "costume": costume, "ghost": ghost or lk["ghost"]})
    idx = {c["name"]: k for k, c in enumerate(cast)}
    lines, prev_scene, place = [], -1, None
    prompts = []
    for sc in scenes:   # one accurate picture prompt per scene; a scene that names no place stays where the last one was
        pr, place = sp.place_prompt(sc, place, names); prompts.append(pr)
    for l in spoken:
        sc = scenes[l["scene"]]; setup, tod = sp.direct(sc); first = l["scene"] != prev_scene; prev_scene = l["scene"]
        who = idx.get(l["speaker"], 0)
        if l["speaker"].lower().startswith("ghost"):
            setup = "ghost"
        elif not first or not setup:
            setup = "closeup" if "!" in l["say"] or not setup else ("talk" if l["speaker"] != "narrator" else setup)
        mood = sp.mood(l, setup)
        lines.append({"say": l["say"], "speaker": l["speaker"], "setup": setup, "mood": mood, "who": who, "label": sp.LABEL.get(setup, ""),
                      "tod": tod, "ground": "sea" if setup in ("sea", "storm") else "floor" if setup in ("temple", "throne", "forge") else "grass",
                      "hl": "", "sfx": sp.sfx_tags(sc["sfx"]) if first else [], "scene_visual": sc["visual"], "beats": sc.get("beats", []), "camera": sc.get("camera", []), "scene_title": sc["title"], "image": prompts[l["scene"]], "scene": l["scene"],
                      "fx": sp.fx_tags(sc["visual"]), "music": sp.music_feel(sc)})
    # voices: Hindi scripts get the free Hindi Edge voices; each character a different pitch/speed so they sound distinct
    from toon import VOICES, MOOD
    tweaks = [("-6Hz", "-2%"), ("+10Hz", "+6%"), ("-1Hz", "+3%"), ("+5Hz", "-3%"), ("-10Hz", "+0%")]
    for k, c in enumerate(cast):
        if hindi:
            c["voice"] = HINDI_VOICES[c["gender"]]; c["pitch"], c["rate"] = tweaks[k % len(tweaks)]
            if c["ghost"]:
                c["pitch"], c["rate"] = "-18Hz", "-12%"
        else:
            c["voice"] = VOICES[(c["gender"], "adult")][k % len(VOICES[(c["gender"], "adult")])]
            c["pitch"], c["rate"] = ("-14Hz", "-10%") if c["ghost"] else ("+0Hz", "+0%")
    for ln in lines:
        if ln["speaker"] == "narrator":
            if hindi:
                ln["voice"] = HINDI_VOICES["male"]
            ln["rate"] = "-4%"
        else:
            c = cast[idx[ln["speaker"]]]; mr, mp = MOOD.get(ln["mood"], MOOD["calm"])
            ln["voice"], ln["pitch"] = c["voice"], c["pitch"]; ln["rate"] = c["rate"] if c["ghost"] else mr
    skill_voice(lines, cast)
    title = next((s["title"] for s in scenes if s["title"]), "My story")
    print(f"  screenplay: {len(scenes)} scenes, {len(lines)} spoken lines, {'Hindi' if hindi else 'English'} voices, cast: "
          + ", ".join(f"{c['name']} ({c['costume']}{', ghost' if c['ghost'] else ''}{', ' + c['prop'] if c.get('prop') else ''}"
                      f"{''.join(', ' + e for e in c.get('extras', []))})" for c in cast))
    return {"title": title[:70], "description": " ".join(s["title"] for s in scenes)[:300], "tags": [], "thumb_text": title.upper()[:24],
            "lines": lines, "cast": cast, "hindi": hindi}


def _render_segments(tl, work, env, out):
    # like the skill's make.sh: render the shots in parallel workers, then join them
    shots = _count_shots(tl)
    workers = max(1, min(int(os.environ.get("WORKERS", os.cpu_count() or 4)), 8, shots))
    procs = []
    os.makedirs(os.path.join(work, "seg"), exist_ok=True)
    for w in range(workers):
        ids = ",".join(str(i) for i in range(w, shots, workers))
        if ids:
            procs.append(subprocess.Popen(["node", os.path.join(work, "render.js"), "segments", ids], cwd=work, env=env,
                                          stdout=open(os.path.join(work, "seg", f"log{w}.txt"), "w"), stderr=subprocess.STDOUT))
    print(f"  rendering {shots} shots with {workers} workers (stick-figure skill make.sh)")
    if any(p.wait() for p in procs):
        raise SystemExit("A stick shot failed to render; see the seg/log*.txt files in the work folder.")
    segs = sorted((f for f in os.listdir(os.path.join(work, "seg")) if re.fullmatch(r"shot_\d+\.mp4", f)), key=lambda f: int(re.findall(r"\d+", f)[0]))
    if len(segs) != shots:
        raise SystemExit(f"Only {len(segs)} of {shots} stick shots rendered.")
    open(os.path.join(work, "seg", "list.txt"), "w").writelines(f"file '{f}'\n" for f in segs)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", out], check=True, cwd=os.path.join(work, "seg"))


def _count_shots(tl):
    """Same rule as stick/auto_shots.js: a line longer than 4.2 s becomes two shots (the skill keeps shots 2-4 s)."""
    n = 0
    for i, sg in enumerate(tl["segs"]):
        a = 0 if i == 0 else sg["start"]; b = tl["segs"][i + 1]["start"] if i + 1 < len(tl["segs"]) else tl["total"]
        n += 2 if (b - a) > 4.2 and sg.get("setup") not in SINGLE else 1
    return n


SINGLE = ("bigtext", "reveal", "blueprint", "treasuremap", "temple")


BG_STYLE = "detailed cartoon background art, painterly, rich colours, cinematic lighting, wide shot, empty scene"
BG_NEG = "people, person, human, man, woman, child, character, face, body, hands, crowd, text, letters, watermark"


BD_PROPS = [(("treasure chest", "chest", "gold coins", "treasure"), "chest"), (("table", "desk"), "table"), (("map",), "map"),
            (("campfire", "bonfire", "fire"), "campfire"), (("door", "gate"), "door"), (("throne",), "throne"), (("lamp", "lantern", "street light"), "lamp")]
BD_EXTRA_PLACES = [(("temple", "ruins", "stone door", "skull symbol", "pyramid", "मंदिर"), "temple"), (("street", "road", "market"), "street"),
                   (("kingdom", "king", "queen", "throne", "palace"), "kingdom")]


PAL_ENVS = {"savanna", "jungle", "forest", "desert", "snow", "beach", "ocean", "ship", "city", "village", "farm", "mountain", "cave", "space", "moon",
            "room", "castle", "graveyard", "temple", "kingdom", "street"}


def paint_backgrounds(tl):
    """Reads each scene's Visual text (or the line itself) -> what to paint: place, time of day, objects, effects."""
    import world, screenplay as sp
    env, tod, prev = None, "day", None
    for i, sg in enumerate(tl["segs"]):
        vis = str(sg.get("scene_visual") or sg.get("image") or "").lower(); say = str(sg.get("text") or "").lower()
        key = sg.get("scene") if sg.get("scene") is not None else vis[:60] or i
        if key != prev:
            prev = key; t = vis or say
            if sg.get("image") and sg.get("scene_visual"):   # a screenplay: its scene prompt already names the place (first mentioned, carried over)
                pl = str(sg["image"]).lower()
                SCREEN = [("a pirate ship in a violent storm", "ocean"), ("captain's cabin", "room"), ("deck", "ship"), ("island", "beach"), ("jungle", "jungle"),
                          ("temple corridor", "temple"), ("stone temple", "temple"), ("treasure chamber", "temple"), ("graveyard", "graveyard"), ("castle hall", "kingdom"),
                          ("battlefield", "kingdom"), ("forge", "village"), ("old house", "room"), ("town street", "street"), ("deep space", "space"),
                          ("laboratory", "room"), ("desert", "desert"), ("mountains", "mountain"), ("ocean", "ocean")]
                t = next((e for k, e in SCREEN if k in pl[:70]), None) or t
            hits =[(0, t)] if t in PAL_ENVS else [(min(t.find(w) for w in ws if world._has(t, w)), v) for ws, v in BD_EXTRA_PLACES + world.PLACES if any(world._has(t, w) for w in ws)]
            env = min(hits)[1] if hits else (env or {"sea": "ocean", "storm": "ocean", "jungle": "jungle", "temple": "temple", "ghost": "graveyard", "skeletons": "graveyard",
                                                     "throne": "kingdom", "forge": "village", "armies": "kingdom", "kingdoms": "kingdom", "night": "village"}.get(sg.get("setup"), "village"))
            tod = world._first(t, world.TOD) or sg.get("tod") or ("night" if env in ("graveyard", "space") else tod)
            props = [p for ws, p in BD_PROPS if any(world._has(vis or say, w) for w in ws)][:3]
        if not sg.get("fx"):
            sg["fx"] = sp.fx_tags(vis + " " + say)
        if not sg.get("music"):
            sg["music"] = sp.music_feel(vis + " " + say)
        if not sg.get("bgspec"):
            sg["bgspec"] = {"env": env, "tod": tod, "props": props, "seed": 11 + __import__("zlib").crc32(str(key).encode()) % 97}
    print("  painted backgrounds from the script: " + " > ".join(dict.fromkeys(f"{s['bgspec']['env']}/{s['bgspec']['tod']}" for s in tl["segs"])), flush=True)


def ai_backgrounds(tl, web, g):
    """'ai' mode: one AI illustration per scene, made from the script's visual details (the screenplay's Visual notes,
    or the writer's 'image' line), drawn behind the stick characters like the reference videos."""
    import imagegen
    from PIL import Image
    os.makedirs(os.path.join(web, "bg"), exist_ok=True); made = {}; last = None
    cap = load_config()["image"].get("max_images", 24); style = g.get("image_style", "")
    for i, sg in enumerate(tl["segs"]):
        key = sg.get("scene") if sg.get("scene") is not None else i   # screenplay: one picture per scene
        if key in made:
            sg["bg"] = made[key]; continue
        if len(made) >= cap:
            sg["bg"] = last; continue
        prompt = (sg.get("image") or sg.get("text") or "").strip()
        if not sg.get("music"):
            import screenplay as _sp; sg["music"] = _sp.music_feel(prompt + " " + str(sg.get("text", "")))
        if not sg.get("fx"):   # written stories: take the animation cues from the picture line too
            import screenplay as _sp; sg["fx"] = _sp.fx_tags(prompt + " " + str(sg.get("text", "")))
        out = os.path.join(web, "bg", f"bg{i}.png")
        try:
            imagegen.generate(prompt, out, True, BG_STYLE + (", " + style.split(",")[0] if style else ""), seed=i,
                              suffix="no people, highly detailed environment", negative_extra=BG_NEG)
            im = Image.open(out).convert("RGB"); W, H = 1080, 1920; k = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * k + .5), int(im.height * k + .5)), Image.LANCZOS)
            x0, y0 = (im.width - W) // 2, (im.height - H) // 2
            im.crop((x0, y0, x0 + W, y0 + H)).save(out.replace(".png", ".jpg"), quality=90); os.remove(out)
            made[key] = last = f"bg/bg{i}.jpg"; sg["bg"] = last
            print(f"  scene background {len(made)}: {prompt[:70]}")
        except Exception as e:
            print(f"  background {i} failed ({type(e).__name__}: {str(e)[:80]}); using the drawn scene")
            sg["bg"] = last
    return made


# ---------------- screenplay steps -> stick shots (each Visual step its own shot, its own people, props and impact) ----------------
ROLE_COSTUME = {"soldier": "helmet", "legionary": "helmet", "legionnaire": "helmet", "warrior": "helmet", "knight": "helmet", "guard": "helmet", "hoplite": "helmet",
                "gladiator": "helmet", "spartan": "helmet", "roman": "helmet", "greek": "helmet", "samurai": "helmet", "viking": "helmet", "king": "crown", "queen": "crown",
                "emperor": "crown", "pharaoh": "crown", "prince": "crown", "princess": "crown", "wizard": "wizard", "monk": "hood", "priest": "hood", "archer": "hood",
                "pirate": "bandana", "sailor": "sailor", "captain": "captain", "blacksmith": "cap", "smith": "cap", "worker": "cap", "builder": "cap", "farmer": "cap",
                "scribe": "hood", "chef": "cap", "police": "cap", "officer": "cap"}
ROLE_COLS = {"soldier": ["#8a2a2a", "#c8a04a"], "legionary": ["#b3202a", "#e6b422"], "legionnaire": ["#b3202a", "#e6b422"], "roman": ["#b3202a", "#e6b422"],
             "knight": ["#9aa3ad", "#9aa3ad"], "warrior": ["#7a4a2a", "#c8a04a"], "king": ["#6a2a8a", "#e6b422"], "scientist": ["#f2f4f6", "#f2f4f6"],
             "doctor": ["#f2f4f6", "#f2f4f6"], "blacksmith": ["#6a4426", "#3a2414"], "scribe": ["#e8dcc0", "#e8dcc0"], "police": ["#2a3a6a", "#2a3a6a"]}
STICK_PLACES = [(("colosseum", "arena", "amphitheatre", "amphitheater", "ancient rome", "rome"), "arena"), (("test range", "shooting range", "firing range", "range"), "range"),
                (("battlefield", "battle field"), "kingdom"), (("forge", "smithy", "workshop"), "village")]
ENV_MAP = {"lab": "room", "office": "room", "hallway": "room", "park": "village", "virtual": "farm", "street": "street", "savanna": "desert"}
PROP_WORDS = [(("bullet", "bullets", "9mm", "calibre", "caliber", "round"), "bullet"), (("gun", "pistol", "rifle", "musket"), "gun"),
              (("target", "bullseye"), "target"), (("breastplate", "armour", "armor", "cuirass", "lorica", "plate", "vest", "chain mail", "chainmail"), "armour"),
              (("sword", "blade", "gladius"), "sword"), (("shield", "scutum"), "shield"), (("bow", "arrow"), "bow"), (("hammer", "anvil"), "anvil"),
              (("blood", "bloodied", "wound", "scar"), "blood")]
LIB2D = {"computer": "screen", "document": "document", "sign": "sign", "jar": "jar", "bench": "table", "chair": "table"}


def _person_look(a, j):
    role = str(a.get("role") or a.get("noun") or ""); near = str(a.get("near") or "").lower()
    costume = ROLE_COSTUME.get(role) or a.get("costume") if a.get("costume") not in (None, "none", "bandana") else ROLE_COSTUME.get(role, "none")
    if any(w in near for w in ("helmet", "armour", "armor", "breastplate")):
        costume = "helmet"
    cols = ROLE_COLS.get(role) or (["#f2f4f6", "#f2f4f6"] if a.get("coat") else None) or a.get("cols") or [["#2f63c9", "#2f63c9"], ["#3fa35b", "#3fa35b"], ["#e0a83a", "#e0a83a"]][j % 3]
    hats = {"bandana": "bandana", "sailor": "sailor", "captain": "captain"}
    o = {"hat": hats.get(costume, "nohat"), "acc": costume if costume not in hats else "none", "hatCol": cols[0], "dotCol": "#fff", "cols": cols,
         "extras": (["glasses"] if role in ("scientist", "professor", "doctor", "researcher") else []) + (["beard"] if a.get("old") else []), "propName": None, "size": 1.0}
    if any(w in near for w in ("vest", "breastplate", "armour", "armor", "chain mail")):
        o["vest"] = "#8a9099"
    for w, pn in (("sword", "sword"), ("gladius", "sword"), ("spear", "spear"), ("shield", "shield"), ("bow", "bow"), ("hammer", "hammer"), ("staff", "staff"), ("lantern", "lantern")):
        if w in near:
            o["propName"] = pn; break
    return o


def expand_steps(sc, tl, g):
    """Lines with Visual steps -> one stick shot per step (people, props, place, action, camera, impact). Returns new segs."""
    if not any(s.get("beats") for s in tl["segs"]):
        return tl["segs"]
    import world, zdf as Z
    world.plan(sc, tl, g)
    steps, _lines = world._segments(tl)
    out, prev_env, prev_wenv = [], None, None
    PRESENTER = {"hat": "nohat", "acc": "none", "hatCol": "#2f63c9", "dotCol": "#fff", "cols": ["#2f63c9", "#2f63c9"], "extras": [], "propName": None, "size": 1.0}
    covered = [w for ws, _ in PROP_WORDS + STICK_PLACES for w in ws] + ["colosseum", "rome", "range"]
    for i, st in enumerate(steps):
        src = next((s for s in tl["segs"] if s["start"] <= st["start"] + 1e-3 and s is not None), tl["segs"][0])
        for s in tl["segs"]:
            if s["start"] <= st["start"] + 1e-3:
                src = s
        t = (" " + str(st.get("text") or "") + " ").lower()
        named = next((v for ws, v in STICK_PLACES if any(w in t for w in ws)), None)
        if named:
            env = named
        elif prev_env and st.get("env") == prev_wenv:   # the step names no new place: stay where we are
            env = prev_env
        else:
            env = ENV_MAP.get(st.get("env"), st.get("env") or "village")
        prev_env, prev_wenv = env, st.get("env")
        people = [_person_look(a, j) for j, a in enumerate(st.get("actors", [])) if a.get("type") in ("person", "ghost", "robot", None)][:3]
        props = [{"kind": k} for ws, k in PROP_WORDS if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) for w in ws)]
        for o in st.get("props", []):
            k = LIB2D.get(o["kind"]) or ("thing" if o["kind"] == "custom" and not any(w in o.get("name", "") for w in covered) else None)
            if k and k not in [p["kind"] for p in props]:
                props.append({"kind": k, "text": (o.get("text") or [o.get("name", "")])[:3], "hl": o.get("hlLine")})
        q = re.findall(r"[\"']([^\"']{3,40})[\"']", str(st.get("text") or ""))
        if q and not any(p["kind"] in ("screen", "sign", "document") for p in props):
            props.append({"kind": "sign", "text": q[:2]})
        weapon = Z.world._first(t, Z.WEAPONS)
        impact = weapon if weapon and any(re.search(r"(?<![a-z])" + h + r"(?![a-z])", t) for h in Z.HITS + ("hitting", "hits", "striking", "against")) else None
        if impact == "bullet" and not any(p["kind"] in ("armour", "target") for p in props) and not people:
            props.append({"kind": "armour"})
        shot = st.get("shot") or "wide"; action = (st.get("acts") or ["idle"])[0] if st.get("acts") else "idle"
        setup = "impact2" if impact else ("closeup" if shot in ("closeup", "ecu") and people and not props else
                                          "walk" if action in ("walk", "ride") else "run" if action in ("run", "chase") else
                                          "crowd" if len(people) >= 3 else "talk" if len(people) == 2 else "single")
        seg = {k: src.get(k) for k in ("mood", "who", "label", "hl", "speaker", "fx", "music")}
        seg.update(start=st["start"], dur=None, setup=setup, tod=st.get("tod") or "day", ground="grass", words=[], scene=f"step{i}",
                   people=people or ([] if impact else [PRESENTER]), props2d=props[:3], impact=impact, propFocus=bool(props) and (shot in ("closeup", "ecu", "dolly_in") or not people),
                   bgspec={"env": env, "tod": st.get("tod") or "day", "props": [], "seed": 11 + i * 7}, act=action)
        out.append(seg)
    print(f"  stick: {len(out)} shots from the script's Visual steps", flush=True)
    return out


def render(sc, tl, d, g, size=(1080, 1920), ai=False):
    """Builds a web folder from the engine + our shots, renders it with the engine's own renderer -> d/video.mp4.
    ai=True: every shot is an AI-illustrated background with the stick characters acting on it."""
    if not (ENGINE / "template" / "web" / "chars.js").exists():
        raise SystemExit("stick mode needs vendor/animation-skills (the workflow checks it out). Locally: "
                         "git clone https://github.com/artemnovitckii/claude-animation-skills vendor/animation-skills")
    work = os.path.join(d, "stick"); web = os.path.join(work, "web")
    shutil.rmtree(work, ignore_errors=True); shutil.copytree(ENGINE / "template" / "web", web)
    open(os.path.join(web, "shots.js"), "w", encoding="utf-8").write(
        open(ROOT / "stick" / "backdrop.js", encoding="utf-8").read() + "\n" + open(ROOT / "stick" / "auto_shots.js", encoding="utf-8").read())
    words = []   # captions follow the spoken lines
    for k, s in enumerate(tl["segs"]):
        for w in s.get("words", []):
            words.append({"w": w["w"], "s": w["s"], "e": w["e"], "line": k})
    tl = dict(tl, segs=expand_steps(sc, tl, g))   # a screenplay: one shot per Visual step (the caller's timeline is untouched)
    paint_backgrounds(tl)   # every scene's background is drawn from the script (also the fallback when an AI picture fails)
    if ai:
        ai_backgrounds(tl, web, g)
    open(os.path.join(web, "words.js"), "w", encoding="utf-8").write("const WORDS=" + json.dumps(words) + ";\n")
    open(os.path.join(web, "warp.js"), "w", encoding="utf-8").write("window.WARP = null;\n")
    engine_hats = {"bandana": "bandana", "sailor": "sailor", "captain": "captain"}   # the rest are drawn by stick/auto_shots.js
    def _look(c, i):
        o = {"hat": engine_hats.get(c["costume"], "nohat"), "acc": c["costume"] if c["costume"] not in engine_hats else "none",
             "hatCol": (c.get("cols") or [None, None])[0] if c["costume"] == "bandana" and c.get("cols") else ['#d8312b', '#6c43c0', '#2f63c9', '#3fa35b'][i % 4],
             "dotCol": "#fff", "ghost": bool(c.get("ghost")), "extras": c.get("extras", []), "propName": c.get("prop"),
             "size": c.get("size", 1.0), "glow": c.get("glow", "#8dffc0")}
        if c.get("cols"):
            o["cols"] = c["cols"]
        if c.get("vest"):
            o["vest"] = c["vest"]
        return o
    cast_js = [f"C(PAL_X('{c['col']}'), {json.dumps(_look(c, i))})" for i, c in enumerate(sc["cast"])]
    data = {"segs": [{k: s.get(k) for k in ("start", "dur", "setup", "mood", "who", "label", "tod", "ground", "hl", "words", "speaker", "bg", "fx", "bgspec", "people", "props2d", "impact", "propFocus", "act")} for s in tl["segs"]],
            "total": tl["total"], "style": {"accent": g.get("thumb_color", "#e0392f")}}
    open(os.path.join(web, "stick_data.js"), "w", encoding="utf-8").write(
        "window.STICK = " + json.dumps(data) + ";\nconst PAL_X = k => ({ cols: PAL[k] || PAL.red });\n"
        "const C0 = (a, b) => Object.assign({}, a, b);\n"
        f"window.STICK.cast = [{', '.join(x.replace('C(', 'C0(', 1) for x in cast_js)}];\n"
        # preload the AI backgrounds; the renderer waits for them before drawing frame 0
        "window.BG = {}; window.__imagesReady = Promise.all([...new Set(window.STICK.segs.map(s => s.bg).filter(Boolean))].map(src => new Promise(r => {"
        " const im = new Image(); im.onload = im.onerror = () => r(); im.src = src; window.BG[src] = im; })));\n")
    # captions: keep combining marks (\p{M}) so Hindi and other scripts render correctly
    mj = os.path.join(web, "main.js"); js = open(mj, encoding="utf-8").read()
    js = js.replace("[^\\p{L}\\p{N}% ]", "[^\\p{L}\\p{M}\\p{N}% ]")
    # captions like the reference videos: bold UPPERCASE words in the top third, thicker outline
    js = js.replace("s.toLowerCase()", "s.toUpperCase()").replace("ctx.translate(540, 1345)", "ctx.translate(540, 470)")
    js = js.replace("0, 0, 70, '#fff', '#111', 13", "0, 0, 86, '#fff', '#111', 18").replace("0, 0, 70, '#fff', '#111', 0", "0, 0, 86, '#fff', '#111', 0")
    open(mj, "w", encoding="utf-8").write(js)
    # the engine's renderer, waiting for the backgrounds to load
    rj = open(ENGINE / "tools" / "render.js", encoding="utf-8").read()
    rj = rj.replace("const total = await page.evaluate(() => window.TOTAL_FRAMES);",
                    "await page.evaluate(() => window.__imagesReady || null);\n  const total = await page.evaluate(() => window.TOTAL_FRAMES);")
    open(os.path.join(work, "render.js"), "w", encoding="utf-8").write(rj)
    html = open(os.path.join(web, "index.html"), encoding="utf-8").read()
    html = html.replace('<script src="shots.js"></script>', '<script src="stick_data.js"></script><script src="shots.js"></script>')
    open(os.path.join(web, "index.html"), "w", encoding="utf-8").write(html)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"))
    if os.environ.get("STICK_CHROME"):
        env["CHROME"] = os.environ["STICK_CHROME"]
    out = os.path.join(work, "silent.mp4")
    import hf
    done = False
    if hf.available():   # HyperFrames captures the frames from the engine's renderFrame() via its seek protocol
        try:
            hf.render(hf.stick_project(web, tl["total"]), out); done = True
        except Exception as e:
            print(f"  HyperFrames render failed ({str(e)[:200]}); using the skill's parallel workers")
    if not done:
        _render_segments(tl, work, env, out)
    W, H = size
    if W > H:   # the engine draws 9:16; for landscape put it on a blurred, widened copy of itself
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", out, "-filter_complex",
                        f"[0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.1[bg];"
                        f"[0]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        os.path.join(d, "video.mp4")], check=True)
    else:
        shutil.copy(out, os.path.join(d, "video.mp4"))
