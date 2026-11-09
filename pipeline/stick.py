"""stick mode: a stick-figure explainer/story made with the stick-figure engine of claude-animation-skills
(MIT, Artem Novitckii; checked out by the workflow into vendor/animation-skills). The engine's rig, props,
whip transitions, 1-2 word lowercase Poppins captions and grade are used as they are; stick/auto_shots.js
turns our story timeline into its shot list automatically."""
import json, os, shutil, subprocess
import requests
from common import load_config, ROOT, FFMPEG

ENGINE = ROOT / "vendor" / "animation-skills" / "skills" / "stick-figure" / "engine"
SETUPS = ["closeup", "talk", "walk", "run", "crowd", "object", "reveal", "night", "impact", "sea", "bigtext", "think"]
MOODS = ["calm", "happy", "scared", "shocked", "angry", "sad", "smug", "dizzy", "think"]
COLS = ["red", "blue", "yellow", "green", "navy", "purple"]

PROMPT = """You write a {seconds}-second vertical stick-figure cartoon video. Genre: {genre}. Style: {tone}
Make ONE completely original story or explainer (never copy existing videos). Idea: {idea}
{inspo}
Structure (from the stick-figure skill): a hook that starts in action, the common belief, a turn on "But",
examples that build, one shot that shows how it works, and a payoff that answers the hook. One idea per line, 6-14 words.
For every line choose a "setup" (what we see): closeup (big face reacting), talk (two characters), walk, run, crowd,
object (a crate labelled with "label"), reveal (a chest opens; "label" pops out), night (dark, lantern, scared),
impact (comic burst with "label" like BOOM), sea (ship on the sea), bigtext ("label" in huge letters), think (question marks).
Change the setup every line. "mood" is one of: {moods}. "time_of_day": day, dusk, night or dawn.
"ground": grass, sand, snow, road, floor or sea.
Reply with JSON only:
{{"title": "under 60 chars", "description": "2 sentences", "tags": ["5-8 tags"], "thumb_text": "2-4 WORDS",
  "characters": [{{"name": "...", "color": "red|blue|yellow|green|navy|purple", "hat": "bandana|sailor|captain|none"}}],
  "lines": [{{"say": "...", "setup": "closeup", "mood": "calm", "who": 0, "label": "", "time_of_day": "day", "ground": "grass", "hl": "KEYWORD"}}]}}
"who" is the index of the character on screen. Write about {lines} lines. The last line ends with: "{cta}" """

MORE = """Continue this {genre} stick-figure video with about {lines} more lines in the same JSON line format
(say, setup, mood, who, label, time_of_day, ground, hl), building toward the payoff. Last lines so far: {last}
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
        lines.append({"say": str(l["say"]).strip(), "setup": setup, "mood": _pick(l.get("mood"), MOODS, "calm"), "who": who,
                      "label": str(l.get("label") or "")[:16], "tod": _pick(l.get("time_of_day"), ["day", "dusk", "night", "dawn"], "day"),
                      "ground": _pick(l.get("ground"), ["grass", "sand", "snow", "road", "floor", "sea"], "grass"),
                      "hl": str(l.get("hl") or "").upper()[:16]})
    if g["cta"].lower().rstrip(".") not in lines[-1]["say"].lower():
        lines.append({"say": g["cta"], "setup": "bigtext", "mood": "happy", "who": 0, "label": g["cta"].split()[0], "tod": "day", "ground": "grass", "hl": ""})
    # genre conditions: dark genres stay at night/dusk, with scared moods and the lantern scene, whatever the LLM picked
    dark = {"horror": ("night", "dusk"), "mystery": ("night", "dusk", "dawn")}.get(g["name"])
    if dark:
        for k, ln in enumerate(lines):
            if ln["tod"] not in dark:
                ln["tod"] = dark[k % len(dark)] if g["name"] == "mystery" else "night"
            if g["name"] == "horror" and ln["mood"] in ("calm", "happy") and ln["setup"] != "bigtext":
                ln["mood"] = "scared" if k % 2 else "shocked"
            if g["name"] == "horror" and ln["setup"] in ("sea", "crowd") and k % 2:
                ln["setup"] = "night"
    lines[0]["setup"] = "closeup" if lines[0]["setup"] not in ("closeup", "impact", "run") else lines[0]["setup"]
    cast = []
    for i, c in enumerate(chars):
        col = _pick(c.get("color"), COLS, COLS[i % len(COLS)]); hat = _pick(c.get("hat"), ["bandana", "sailor", "captain", "none"], "bandana")
        cast.append({"name": str(c.get("name") or f"Hero{i}"), "col": col, "hat": hat})
    print(f"  stick story: {story.get('title')!r}, {len(lines)} lines, cast: {', '.join(c['name'] for c in cast)}")
    return {"title": str(story.get("title") or idea)[:70], "description": str(story.get("description") or idea),
            "tags": [str(t) for t in story.get("tags", [])][:10], "thumb_text": str(story.get("thumb_text") or "WHAT IF")[:24],
            "lines": lines, "cast": cast}


def render(sc, tl, d, g, size=(1080, 1920)):
    """Builds a web folder from the engine + our shots, renders it with the engine's own renderer -> d/video.mp4."""
    if not (ENGINE / "template" / "web" / "chars.js").exists():
        raise SystemExit("stick mode needs vendor/animation-skills (the workflow checks it out). Locally: "
                         "git clone https://github.com/artemnovitckii/claude-animation-skills vendor/animation-skills")
    work = os.path.join(d, "stick"); web = os.path.join(work, "web")
    shutil.rmtree(work, ignore_errors=True); shutil.copytree(ENGINE / "template" / "web", web)
    shutil.copy(ROOT / "stick" / "auto_shots.js", os.path.join(web, "shots.js"))
    words = []
    for k, s in enumerate(tl["segs"]):
        for w in s.get("words", []):
            words.append({"w": w["w"], "s": w["s"], "e": w["e"], "line": k})
    open(os.path.join(web, "words.js"), "w", encoding="utf-8").write("const WORDS=" + json.dumps(words) + ";\n")
    open(os.path.join(web, "warp.js"), "w", encoding="utf-8").write("window.WARP = null;\n")
    hats = {"bandana": "bandana", "sailor": "sailor", "captain": "captain", "none": "nohat"}
    cast_js = [f"C(PAL_X('{c['col']}'), {{ hat: '{hats[c['hat']]}', hatCol: '{['#d8312b', '#6c43c0', '#2f63c9', '#3fa35b'][i % 4]}', dotCol: '#fff' }})" for i, c in enumerate(sc["cast"])]
    data = {"segs": [{k: s.get(k) for k in ("start", "dur", "setup", "mood", "who", "label", "tod", "ground", "hl", "words")} for s in tl["segs"]],
            "total": tl["total"], "style": {"accent": g.get("thumb_color", "#e0392f")}}
    open(os.path.join(web, "stick_data.js"), "w", encoding="utf-8").write(
        "window.STICK = " + json.dumps(data) + ";\nconst PAL_X = k => ({ cols: PAL[k] || PAL.red });\n"
        "const C0 = (a, b) => Object.assign({}, a, b);\n"
        f"window.STICK.cast = [{', '.join(x.replace('C(', 'C0(', 1) for x in cast_js)}];\n")
    html = open(os.path.join(web, "index.html"), encoding="utf-8").read()
    html = html.replace('<script src="shots.js"></script>', '<script src="stick_data.js"></script><script src="shots.js"></script>')
    open(os.path.join(web, "index.html"), "w", encoding="utf-8").write(html)
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"))
    if os.environ.get("STICK_CHROME"):
        env["CHROME"] = os.environ["STICK_CHROME"]
    out = os.path.join(work, "silent.mp4")
    subprocess.run(["node", str(ENGINE / "tools" / "render.js"), "video", out], check=True, cwd=work, env=env)
    W, H = size
    if W > H:   # the engine draws 9:16; for landscape put it on a blurred, widened copy of itself
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", out, "-filter_complex",
                        f"[0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.1[bg];"
                        f"[0]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                        os.path.join(d, "video.mp4")], check=True)
    else:
        shutil.copy(out, os.path.join(d, "video.mp4"))
