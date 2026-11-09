"""stick mode: a stick-figure explainer/story made with the stick-figure engine of claude-animation-skills
(MIT, Artem Novitckii; checked out by the workflow into vendor/animation-skills). The engine's rig, props,
whip transitions, 1-2 word lowercase Poppins captions and grade are used as they are; stick/auto_shots.js
turns our story timeline into its shot list automatically."""
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
STRUCTURE = {"science": EXPLAIN, "motivation": EXPLAIN, "comedy": FABLE, "history": FABLE, "mystery": FABLE, "horror": STORY, "story": FABLE}

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
                    "costume": "none|crown|helmet|hood|wizard|cap|bandana|sailor|captain"}}],
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
        cast.append({"name": str(c.get("name") or f"Hero{i}"), "col": col, "costume": costume,
                     "gender": _pick(c.get("gender"), ["male", "female"], "male")})
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
        costume = "captain" if "captain" in low else "crown" if ("king" in low or "queen" in low) else "helmet" if "soldier" in low else "bandana"
        gender = "female" if any(w in low for w in ("queen", "girl", "woman", "mother", "lady", "princess", "she")) else "male"
        cast.append({"name": n, "col": ["red", "yellow", "blue", "green", "purple", "navy"][i % 6], "costume": costume, "gender": gender, "ghost": ghost})
    idx = {c["name"]: k for k, c in enumerate(cast)}
    lines, prev_scene = [], -1
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
                      "hl": "", "sfx": sp.sfx_tags(sc["sfx"]) if first else [], "scene_visual": sc["visual"], "scene_title": sc["title"], "image": sc["visual"][:300], "scene": l["scene"]})
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
          + ", ".join(f"{c['name']} ({c['costume']}{', ghost' if c['ghost'] else ''})" for c in cast))
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


BG_STYLE = ("detailed digital cartoon illustration, storybook background art, painterly, rich colours, soft cinematic lighting, "
            "wide establishing shot, empty scene")
BG_NEG = "people, person, human, man, woman, child, character, face, body, hands, crowd, text, letters, watermark"


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


def render(sc, tl, d, g, size=(1080, 1920), ai=False):
    """Builds a web folder from the engine + our shots, renders it with the engine's own renderer -> d/video.mp4.
    ai=True: every shot is an AI-illustrated background with the stick characters acting on it."""
    if not (ENGINE / "template" / "web" / "chars.js").exists():
        raise SystemExit("stick mode needs vendor/animation-skills (the workflow checks it out). Locally: "
                         "git clone https://github.com/artemnovitckii/claude-animation-skills vendor/animation-skills")
    work = os.path.join(d, "stick"); web = os.path.join(work, "web")
    shutil.rmtree(work, ignore_errors=True); shutil.copytree(ENGINE / "template" / "web", web)
    shutil.copy(ROOT / "stick" / "auto_shots.js", os.path.join(web, "shots.js"))
    if ai:
        ai_backgrounds(tl, web, g)
    words = []
    for k, s in enumerate(tl["segs"]):
        for w in s.get("words", []):
            words.append({"w": w["w"], "s": w["s"], "e": w["e"], "line": k})
    open(os.path.join(web, "words.js"), "w", encoding="utf-8").write("const WORDS=" + json.dumps(words) + ";\n")
    open(os.path.join(web, "warp.js"), "w", encoding="utf-8").write("window.WARP = null;\n")
    engine_hats = {"bandana": "bandana", "sailor": "sailor", "captain": "captain"}   # the rest are drawn by stick/auto_shots.js
    cast_js = [f"C(PAL_X('{c['col']}'), {{ hat: '{engine_hats.get(c['costume'], 'nohat')}', acc: '{c['costume'] if c['costume'] not in engine_hats else 'none'}', "
               f"hatCol: '{['#d8312b', '#6c43c0', '#2f63c9', '#3fa35b'][i % 4]}', dotCol: '#fff', ghost: {'true' if c.get('ghost') else 'false'} }})" for i, c in enumerate(sc["cast"])]
    data = {"segs": [{k: s.get(k) for k in ("start", "dur", "setup", "mood", "who", "label", "tod", "ground", "hl", "words", "speaker", "bg")} for s in tl["segs"]],
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
