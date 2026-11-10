"""zach-d-films mode: the claude-animation-skills /zach-d-films engine (3D cartoon "what if" explainer: procedural
people and props, blue studio sky, slow-motion impacts with sparks and the red force ripple, whip cuts, 1-3 word
captions), with the edit BUILT FROM THE SCRIPT instead of the skill's worked example. Each Visual step is a shot;
people, outfits, poses, props (the skill's own or designed for this script) and impacts come from its words."""
import json, os, re, shutil, subprocess
from common import ROOT, FFMPEG
import world

ENGINE = ROOT / "vendor" / "animation-skills" / "skills" / "zach-d-films" / "engine"
WEAPONS = [(("gun", "pistol", "shoot", "shoots", "shot at", "fires", "bullet"), "bullet"), (("arrow", "bow", "archer"), "arrow"),
           (("sword", "blade", "slash"), "sword"), (("mace", "hammer", "club"), "mace")]
HITS = ("hit", "hits", "strike", "strikes", "impact", "smash", "slam", "punch", "shoot", "shoots", "fires", "pierce", "stab", "crash", "collide", "explode", "bounce")
OUTFIT = [(("bulletproof", "bullet-proof", "steel vest", "vest", "kevlar"), "vest"), (("chain mail", "chainmail", "mail shirt"), "chainmail"),
          (("plate armor", "plate armour", "breastplate", "cuirass", "armor", "armour", "steel plates"), "plate"), (("knight",), "knight"), (("archer", "hood"), "archer")]
ROLE_OUTFIT = {"knight": "knight", "archer": "archer", "warrior": "plate", "soldier": "plate", "hoplite": "plate", "gladiator": "plate", "legionary": "plate",
               "legionnaire": "plate", "samurai": "plate", "viking": "chainmail", "spartan": "plate", "roman": "plate", "greek": "plate", "guard": "chainmail"}
ROLE_SHIRT = {"blacksmith": "#6a4426", "smith": "#6a4426", "scribe": "#e8dcc0", "monk": "#7a5a3a", "priest": "#f0ece0", "scientist": "#f2f4f6", "doctor": "#f2f4f6",
              "king": "#8a2a2a", "queen": "#6a2a8a", "pirate": "#d8312b", "farmer": "#5a7a3a", "chef": "#f2f4f6", "police": "#2a3a6a", "officer": "#2a3a6a"}
BATTLE = ("battle", "clash", "fight", "duel", "combat", "war ", "attack")
FORGE = ("forge", "forges", "hammer", "anvil", "blacksmith", "smith")
SHIRTS = ["#3a6ad8", "#d8463a", "#3aa86a", "#e0a83a", "#8a5ad8", "#2a8ab0"]


def _lib_recipe(o):
    """The cinema library's objects as part recipes, so this engine can build them too (jar, screen, document ...)."""
    k, txt = o["kind"], o.get("text") or []
    T = lambda lines, w, h, pos, fg="#6ad8ff", bg="#0b1a2c", hl=None: {"shape": "text", "size": [w, h], "pos": pos, "rot": [0, 0, 0], "color": fg, "bg": bg, "text": "\n".join(lines), **({"hl": hl} if hl is not None else {})}
    if k == "jar":
        return {"parts": [{"shape": "cylinder", "size": [.18, .18, .42], "pos": [0, 1.0, 0], "color": "#cfefff", "opacity": .3},
                          {"shape": "sphere", "size": [.11], "pos": [0, .99, 0], "color": "#f29aae", "glow": .35}, {"shape": "cylinder", "size": [.19, .19, .04], "pos": [0, 1.23, 0], "color": "#7a8a96", "metal": 1},
                          {"shape": "box", "size": [1.4, .06, .7], "pos": [0, .76, 0], "color": "#9a6a3e"}, {"shape": "box", "size": [.06, .76, .06], "pos": [.6, .38, .28], "color": "#7a4a26"},
                          {"shape": "box", "size": [.06, .76, .06], "pos": [-.6, .38, .28], "color": "#7a4a26"}], "motion": "none", "focusY": 1.0, "size": .55}
    if k == "computer":
        return {"parts": [{"shape": "box", "size": [.95, .6, .05], "pos": [0, 1.3, 0], "color": "#1a1d24"}, T(txt or ["DATA"], .88, .52, [0, 1.3, .03], "#ff4a4a" if o.get("error") else "#6ad8ff"),
                          {"shape": "box", "size": [.06, .3, .06], "pos": [0, .9, -.02], "color": "#2a2e36"}, {"shape": "box", "size": [1.4, .06, .7], "pos": [0, .76, 0], "color": "#9a6a3e"},
                          {"shape": "box", "size": [.06, .76, .06], "pos": [.6, .38, .28], "color": "#7a4a26"}, {"shape": "box", "size": [.06, .76, .06], "pos": [-.6, .38, .28], "color": "#7a4a26"}], "motion": "flicker", "focusY": 1.3, "size": .75}
    if k == "document":
        return {"parts": [T(txt or ["CONTRACT"], .5, .7, [0, 1.25, 0], "#2a2a33", "#f6f1e6", o.get("hlLine"))], "motion": "none", "focusY": 1.25, "size": .6}
    if k == "sign":
        return {"parts": [{"shape": "box", "size": [2.6, .75, .08], "pos": [0, 2.2, -.04], "color": "#1a1d24"}, T(txt or ["SIGN"], 2.45, .6, [0, 2.2, .01], "#5ae8ff", "#101420")], "motion": "flicker", "focusY": 2.2, "size": 1.9}
    if k == "machine":
        return {"parts": [{"shape": "box", "size": [.6, 1.0, .5], "pos": [0, .5, 0], "color": "#d8dde4", "metal": 1}, {"shape": "cylinder", "size": [.16, .16, .7], "pos": [-.45, .4, 0], "color": "#4aa8ff", "metal": 1},
                          {"shape": "sphere", "size": [.04], "pos": [-.1, .85, .26], "color": "#5aff8a", "glow": 1.5}, {"shape": "sphere", "size": [.04], "pos": [.1, .85, .26], "color": "#ff5a5a", "glow": 1.5}], "motion": "none"}
    if k == "bicycle":
        return {"parts": [{"shape": "torus", "size": [.33, .03], "pos": [-.5, .35, 0], "color": "#1a1a1a"}, {"shape": "torus", "size": [.33, .03], "pos": [.5, .35, 0], "color": "#1a1a1a"},
                          {"shape": "cylinder", "size": [.025, .025, 1.0], "pos": [0, .55, 0], "rot": [0, 0, 1.2], "color": "#d8312b", "metal": 1}], "motion": "none"}
    if k == "finish":
        return {"parts": [T(["FINISH"], 3.4, .45, [0, 2.1, 0], "#111111", "#ffffff"), {"shape": "cylinder", "size": [.05, .05, 2.3], "pos": [-1.75, 1.15, 0], "color": "#ff3a6a"},
                          {"shape": "cylinder", "size": [.05, .05, 2.3], "pos": [1.75, 1.15, 0], "color": "#3a8aff"}], "motion": "none"}
    if k in ("bench", "chair", "shelf", "cable"):
        return {"parts": [{"shape": "box", "size": [1.4, .06, .7] if k != "chair" else [.5, .06, .5], "pos": [0, .76 if k != "chair" else .48, 0], "color": "#9a6a3e"}], "motion": "none"}
    return {"parts": [], "motion": "none"}


def _cap_chunks(words, maxw=3, maxc=18):   # the skill's captions.py rule: 1-3 words, broken at punctuation
    SMALL = {"a", "an", "the", "at", "to", "of", "in", "on", "and", "or", "but", "for", "with", "by", "it", "is", "like", "as", "so"}
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w); text = " ".join(x["w"] for x in cur)
        stop = re.search(r"[.,?!;:]$", w["w"]); dangling = w["w"].lower() in SMALL and i + 1 < len(words) and len(cur) < maxw + 1
        if stop or ((len(cur) >= maxw or len(text) >= maxc) and not dangling):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [[g[0]["s"], re.sub(r"[.,;:]+$", "", " ".join(x["w"] for x in g))] for g in out]


def plan(sc, tl, g):
    world.plan(sc, tl, g)
    segs, lines = world._segments(tl)
    words = [w for s in tl["segs"] for w in s.get("words", [])]
    caps = _cap_chunks(words)
    if caps:
        caps[-1].append(words[-1]["e"] + .3)
    fades = []
    for ln in lines:   # one dip to black on the "But" turn, like the skill
        if ln["words"] and ln["words"][0]["w"].lower().strip(",.") == "but" and ln["start"] > 1:
            a = ln["start"]; fades = [[a - .18, a, a + .1, a + .26]]; break
    shots = []
    for i, s in enumerate(segs):
        end = segs[i + 1]["start"] if i + 1 < len(segs) else tl["total"]
        t = (" " + str(s.get("text") or "") + " " + " ".join(w["w"] for w in s.get("words", [])) + " ").lower()
        actors = []
        for j, a in enumerate(s.get("actors", [])):
            if a.get("type") not in ("person", "ghost", None) and a.get("type") != "robot":
                continue   # this engine draws people; animals/creatures appear as designed props
            near = " " + str(a.get("near") or t) + " "
            role = str(a.get("role") or a.get("noun") or "")
            wears = re.search(r"\b(wear|wears|wearing|in an?|dressed|armou?red|with an?)\b", near) is not None   # "a man IN a steel vest", not "forge steel plates"
            outfit = (world._first(near, OUTFIT) if wears or not role else None) or ROLE_OUTFIT.get(role) or ("knight" if a.get("costume") == "helmet" else "casual")
            actors.append({"outfit": outfit, "role": role, "shirt": "#f2f4f6" if a.get("coat") else (ROLE_SHIRT.get(role) or (a.get("cols") or [None])[0] or SHIRTS[j % len(SHIRTS)]),
                           "old": a.get("old"), "ghost": a.get("ghost"), "size": a.get("size") if a.get("size") not in (None, 1, 1.0) else None})
        acts = [{"chase": "run", "ride": "sit", "scared": "scared", "happy": "happy", "look": "think", "sit": "sit", "sleep": "sleep", "walk": "walk", "run": "run",
                 "attack": "swing", "roar": "scared"}.get(x, "idle") for x in (s.get("acts") or [])][:len(actors)]
        if "point" in t:
            acts = (["point"] + acts[1:]) if acts else acts
        props = []
        for o in s.get("props", []):
            if o["kind"] == "custom":
                props.append({"kind": "custom", "recipe": o["recipe"]})
            else:
                props.append({"kind": "custom", "recipe": _lib_recipe(o)})
        if not actors:   # never an empty frame: someone is always there to show the idea
            role = next((r for r in world.ROLES if re.search(r"(?<![a-z])" + r + r"(e?s)?(?![a-z])", t)), "")
            actors.append({"outfit": ROLE_OUTFIT.get(role, world._first(t, OUTFIT) or "casual"), "role": role, "shirt": ROLE_SHIRT.get(role, SHIRTS[i % len(SHIRTS)])})
            acts = ["think" if "?" in t or "ponder" in t else "talk"]
        weapon = world._first(t, WEAPONS)
        battle = any(w in t for w in BATTLE)
        if battle and len(actors) < 2:   # a battle needs two sides
            actors.append(dict(actors[0], shirt=SHIRTS[(i + 1) % len(SHIRTS)])); acts = (acts + ["idle"])[:2]
        if battle and not weapon:
            weapon = "sword"
        if any(w in t for w in FORGE):   # the blacksmith hammers glowing steel on an anvil
            props.append({"kind": "custom", "recipe": {"parts": [
                {"shape": "box", "size": [.5, .12, .22], "pos": [0, .62, 0], "color": "#3a3c40", "metal": 1}, {"shape": "box", "size": [.2, .5, .18], "pos": [0, .3, 0], "color": "#2a2c30", "metal": 1},
                {"shape": "box", "size": [.32, .03, .12], "pos": [0, .7, 0], "color": "#ff7a2a", "glow": 2.0}], "motion": "flicker", "focusY": .65, "size": .6}, "at": [.45, 0, .35]})
            acts = ["swing"] + acts[1:]; weapon = weapon if weapon not in (None, "mace") else None
            if not any(p.get("kind") == "mace" for p in props):
                props.append({"kind": "mace", "hold": 0})
        if weapon in ("sword", "mace", "arrow") and not any(p["kind"] in (weapon, "bow") for p in props):
            props.append({"kind": weapon if weapon != "arrow" else "bow", "hold": 0})   # weapons are held, not floating
        impact = {"weapon": weapon} if weapon and (battle or any(re.search(r"(?<![a-z])" + h + r"(?![a-z])", t) for h in HITS)) else None
        if impact and actors:   # the one wearing the armour (or named after 'at') takes the hit
            impact["target"] = next((j for j, a in enumerate(actors) if a["outfit"] in ("vest", "chainmail", "plate")), 1 if len(actors) > 1 else 0)
        for pr in props:   # held weapons go to a person who isn't taking the hit
            if pr.get("kind") in ("sword", "mace", "bow", "shield"):
                pr["hold"] = next((j for j in range(len(actors)) if not impact or j != impact.get("target")), 0)
        shots.append({"start": round(s["start"], 3), "end": round(end, 3), "dur": round(end - s["start"], 3), "actors": actors[:3], "acts": acts, "props": props[:4],
                      "impact": impact, "shot": s.get("shot") or "wide", "shot2": s.get("shot2"), "split": s.get("split"), "focusObj": s.get("focusObj"),
                      "focus": 0, "speaker": s.get("speakerIdx", -1), "words": s.get("words", []), "dark": s.get("tod") == "night"})
    print(f"  zach-d-films: {len(shots)} shots, {len(caps)} captions" + (f", dip to black at {fades[0][1]:.1f}s" if fades else ""), flush=True)
    return {"duration": round(tl["total"], 2), "captions": caps, "fades": fades, "shots": shots}


def _prepare(d, data):
    if not (ENGINE / "src" / "human.js").exists():
        raise SystemExit("zdf mode needs vendor/animation-skills (the workflow checks it out).")
    proj = os.path.join(d, "zdf"); shutil.rmtree(proj, ignore_errors=True); shutil.copytree(ENGINE, proj)
    shutil.copy(ROOT / "zdf" / "auto_shots.js", os.path.join(proj, "src", "shots.js"))
    open(os.path.join(proj, "plan.js"), "w", encoding="utf-8").write("globalThis.ZDF = " + json.dumps(data) + ";\n")
    ix = os.path.join(proj, "index.html"); h = open(ix, encoding="utf-8").read()
    h = h.replace('<script type="module" src="./src/main.js"></script>', '<script src="./plan.js"></script>\n<script type="module" src="./src/main.js"></script>')
    open(ix, "w", encoding="utf-8").write(h)
    # renderer: serve node_modules from the repo, ffmpeg from the pipeline, software GL on machines without a GPU, Windows-safe paths
    rm = os.path.join(proj, "render.mjs"); r = open(rm, encoding="utf-8").read()
    r = r.replace("const ROOT = path.dirname(new URL(import.meta.url).pathname);", "import { fileURLToPath } from 'node:url';\nconst ROOT = path.dirname(fileURLToPath(import.meta.url));\nconst NM = process.env.ZDF_NODE_MODULES;")
    r = r.replace("  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));",
                  "  const u = decodeURIComponent(req.url.split('?')[0]);\n  const p = u.startsWith('/node_modules/') && NM ? path.join(NM, u.slice('/node_modules/'.length)) : path.join(ROOT, u);")
    r = r.replace("const types = { '.html': 'text/html', '.js': 'text/javascript',", "const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',")
    r = r.replace("const browser = await chromium.launch({ args: [...GL, '--ignore-gpu-blocklist'] });",
                  "const browser = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}), args: [...GL, '--ignore-gpu-blocklist'] });")
    r = r.replace("spawn('ffmpeg',", "spawn(process.env.FFMPEG || 'ffmpeg',")
    # speed on CPU-only runners: JPEG frames instead of PNG
    r = r.replace("const shot = () => page.screenshot({ clip: { x: 0, y: 0, width: 720, height: 1280 }, type: 'png' });",
                  "const shot = () => page.screenshot({ clip: { x: 0, y: 0, width: 720, height: 1280 }, type: process.env.ZDF_PNG ? 'png' : 'jpeg', quality: process.env.ZDF_PNG ? undefined : 92 });")
    r = r.replace("'-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-'", "'-f', 'image2pipe', '-framerate', String(fps), '-c:v', process.env.ZDF_PNG ? 'png' : 'mjpeg', '-i', '-'")
    open(rm, "w", encoding="utf-8").write(r)
    # speed: 3/4-resolution 3D (captions stay sharp: they are page text), no MSAA, depth of field only on close-ups
    mj = os.path.join(proj, "src", "main.js"); m = open(mj, encoding="utf-8").read()
    if not os.environ.get("ZDF_FULL"):
        m = m.replace("renderer.setPixelRatio(1);", "renderer.setPixelRatio(0.75);")
        m = m.replace("const rt = new THREE.WebGLRenderTarget(W, H, { samples: 4, type: THREE.HalfFloatType });",
                      "const rt = new THREE.WebGLRenderTarget(W * 0.75, H * 0.75, { samples: 0, type: THREE.HalfFloatType });")
        m = m.replace("bokeh.enabled = dof.aperture > 0;", "bokeh.enabled = dof.aperture > 0.01;")
        m = m.replace("key.shadow.mapSize.set(1536, 1536);", "key.shadow.mapSize.set(1024, 1024);")
    open(mj, "w", encoding="utf-8").write(m)
    env = dict(os.environ, ZDF_NODE_MODULES=str(ROOT / "node_modules"), FFMPEG=FFMPEG, GL=os.environ.get("GL", "swiftshader"))
    if os.environ.get("STICK_CHROME"):
        env["CHROME"] = os.environ["STICK_CHROME"]
    return proj, rm, env


def render(sc, tl, d, g, size=(1080, 1920)):
    proj, rm, env = _prepare(d, plan(sc, tl, g))
    silent = os.path.join(proj, "silent.mp4")
    subprocess.run(["node", rm, "video", silent, "30"], check=True, env=env, cwd=proj)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", silent, "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                    os.path.join(d, "video.mp4")], check=True)


def stills(sc, tl, d, g, times):
    """Quick check of the plan: d/zdf/stills/t_<t>.png."""
    data = plan(sc, tl, g); proj, rm, env = _prepare(d, data)
    subprocess.run(["node", rm, "stills", ",".join(str(t) for t in times), os.path.join(proj, "stills")], check=True, env=env, cwd=proj)
    return proj, data
