"""One command: idea -> script -> voice -> visuals -> music -> final.mp4 -> thumbnail -> (optional) YouTube upload.

  python run.py --genre horror --mode stick --length "30 sec" --orientation portrait
  python run.py --genre comedy --mode 2d
  python run.py --genre history --mode doc --length "5 min" --orientation landscape
  python run.py --idea "your idea"        # skip the YouTube idea search
  python run.py --upload                  # also upload to YouTube (privacy from config.json, default private)
  python run.py --no-llm                  # skip Ollama, use the built-in genre template (narrated modes only)

Every mode is one entry in MODES below: which script writer it uses and which renderer draws it.
There is no fallback between modes: an unknown mode, or a renderer that fails, stops the run with an error.
"""
import argparse, json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))
from common import load_config, genre_cfg, slug, WORK, OUTPUT  # noqa: E402
import ideas, scriptgen, voice, timeline, stock, cinema, thumbnail, toon, stick, reference, storycraft, custom, screenplay  # noqa: E402
import theme  # noqa: E402


# ---------------------------------------------------------------- script writers
def script_narration(a, g, idea, inspo, secs):
    """Narrated story/explainer for the footage modes and cinema (chapters from 1 min)."""
    if secs >= 60:
        return scriptgen.write_long(g, idea, inspo, secs / 60, use_llm=not a.no_llm, doc=a.mode == "doc")
    return scriptgen.write_script(g, idea, inspo, use_llm=not a.no_llm)


def script_toon(a, g, idea, inspo, secs):
    return toon.write_story(g, idea, inspo, secs / 60)


def script_stick(a, g, idea, inspo, secs):
    return stick.write_story(g, idea, inspo, secs)


# ---------------------------------------------------------------- renderers (each writes <work>/video.mp4)
def render_footage(a, sc, durs, gap, d, g, size):
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    timeline.write_ass(tl, os.path.join(d, "captions.ass"), g, size)
    stock.render(tl, d, g, size, a.mode)          # a.mode is stock | ai | mix | doc


def render_toon(a, sc, durs, gap, d, g, size):
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    toon.render(sc, tl, d, g, size)


def render_stick(a, sc, durs, gap, d, g, size):
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    stick.render(sc, tl, d, g, size)


def render_ai(a, sc, durs, gap, d, g, size):
    """AI-illustrated scenes from the script's visual details, with the stick characters acting on them."""
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    stick.render(sc, tl, d, g, size, ai=True)
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)


def render_cinema(a, sc, durs, gap, d, g, size):
    """3D world built from the script: the animals/people/places it names, filmed with the skill's camera angles."""
    import world
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    world.render(sc, tl, d, g, size, fast=not a.full_quality)
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)


def render_zdf(a, sc, durs, gap, d, g, size):
    """zach-d-films skill: 3D cartoon explainer (people, props, slow-motion impacts) with every shot built from the script."""
    import zdf
    tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
    zdf.render(sc, tl, d, g, size)
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)


SCREEN_MODES = ("stick", "ai", "cinema", "zdf")   # these build everything from a scene-by-scene screenplay

MODES = {
    #  mode      script writer       renderer         what it is
    "ai":     (script_stick,     render_ai,      "AI-illustrated scenes from the script's visual details + stick characters"),
    "doc":    (script_narration, render_footage, "documentary: AI stills with camera moves, crossfades, chapter cards"),
    "2d":     (script_toon,      render_toon,    "2D flat-vector cartoon (toon/toon.html, GSAP)"),
    "stick":  (script_stick,     render_stick,   "stick-figure engine from claude-animation-skills (stick/auto_shots.js)"),
    "cinema": (script_stick,     render_cinema,  "3D world built from the script (code-cinema skill: models, places, camera angles)"),
    "zdf":    (script_stick,     render_zdf,     "zach-d-films skill: 3D cartoon 'what if' explainer, shots built from the script"),
}


def parse_length(s):
    """'30 sec' -> 30, '1 min' -> 60, '5' -> 300 (bare numbers are minutes), 'short' -> 30."""
    s = str(s).lower().strip()
    if s.startswith("short"):
        return 30
    n = float(re.match(r"[\d.]+", s).group())
    return int(n) if ("sec" in s or s.endswith("s")) and "min" not in s else int(n * 60)


def main():
    cfg = load_config(); ap = argparse.ArgumentParser()
    ap.add_argument("--genre", default="auto", help="auto (default: the theme is read from your script / reference) or force one of: " + ", ".join(cfg["genres"]))
    ap.add_argument("--mode", default=cfg.get("mode", "stock"), help="; ".join(f"{k}: {v[2]}" for k, v in MODES.items()))
    ap.add_argument("--length", default="30 sec", help="30 sec, 1 min, 3 min, 5 min or 10 min")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"],
                    help="portrait 9:16 (Shorts / Reels) or landscape 16:9 (normal YouTube video)")
    ap.add_argument("--reference", help="optional link (YouTube or any page) to base the idea and tone on")
    ap.add_argument("--script", help="your own script (said word for word, or a full Scene/Visual/Narrator screenplay) - or just a TOPIC: a short line is turned into a full screenplay for the chosen length")
    ap.add_argument("--idea", help="(optional) a starting idea; the Run workflow form no longer has this box"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--full-quality", action="store_true", help="cinema mode: render 3D at full resolution (slower)")
    a = ap.parse_args(); t0 = time.time()
    a.mode = str(a.mode).strip().lower()
    if a.mode not in MODES:
        sys.exit(f"Unknown mode {a.mode!r}. Choose one of: {', '.join(MODES)}")
    if str(a.genre).lower() in ("auto", "", "none"):   # no genre box: the script itself sets the theme
        src = a.script or a.idea or ""
        if not src and a.reference:
            try:
                r0 = reference.read(a.reference); src = f"{r0.get('title', '')} {r0.get('text', '') or r0.get('description', '')}"
            except Exception:
                src = ""
        a.genre = theme.detect(src, cfg["genres"]) or "rotate"
    g = genre_cfg(a.genre); secs = parse_length(a.length); land = a.orientation == "landscape"
    size = cfg["video"]["long_size"] if land else cfg["video"]["size"]
    write_script, render_visuals, what = MODES[a.mode]
    print(f"== mode: {a.mode} ({what})\n== theme: {g['name']}  length: {secs} s  {a.orientation} {size[0]}x{size[1]}", flush=True)

    step = lambda s: print(f"{s}   [{(time.time() - t0) / 60:.1f} min]", flush=True)
    step("1/7 idea")
    topic = None   # a short line in the script box is a topic, not a script: the AI writes the screenplay for the chosen length
    if a.script and not screenplay.looks_like(a.script) and len(a.script.split()) <= 30 and "|" not in a.script and a.script.strip().count("\n") < 2:
        topic, a.script = a.script.strip(), None
        print(f"  topic: {topic!r} (a screenplay will be written for {secs}s)")
    play = stick.from_screenplay(g, a.script) if a.script and screenplay.looks_like(a.script) else None   # a full screenplay
    says = [l["say"] for l in play["lines"]] if play else custom.split(a.script)
    if says:
        print(f"  custom script: {len(says)} lines, {sum(len(s.split()) for s in says)} words (used word for word)")
    if reference.is_link(a.idea) and not a.reference:   # a link pasted into the idea box counts as a reference
        a.reference, a.idea = a.idea.strip(), None
    ref = reference.read(a.reference) if a.reference else None
    if says:
        idea, inspo = (a.idea or says[0]), []
    elif ref:
        idea, inspo = reference.to_idea(ref, a.idea), [ref["title"]]
    else:
        idea, inspo = (topic, []) if topic else ((a.idea, []) if a.idea else ideas.pick_idea(g))
    written = None
    if not says and a.mode in SCREEN_MODES and not a.no_llm:   # topic (or today's idea) -> full screenplay sized to the length
        import screenwriter
        written = screenwriter.write(idea, secs, a.mode, g, inspo)
        if written:
            play = stick.from_screenplay(g, written); says = [l["say"] for l in play["lines"]]
    step(f"2/7 script ({'screenwriter' if written else write_script.__name__})")
    if says:   # your own script: keep every word; the writers only choose what we see
        bible = {}
        if play and a.mode in SCREEN_MODES:
            sc = play
        elif write_script is script_narration:
            sc = custom.narration(g, says)
        else:
            sc = write_script(a, g, custom.brief(says, a.idea), [], secs); sc["lines"] = custom.align(sc["lines"], says)
        if play and sc is not play:   # other modes: keep the screenplay's voices, and use its Visual notes for images/clips
            for l, p in zip(sc["lines"], play["lines"]):
                l.update({k: p[k] for k in ("voice", "rate", "pitch", "speaker") if k in p})
                if p.get("scene_visual") and write_script is script_narration:
                    l["image"] = p["scene_visual"][:300]; l["visual"] = " ".join(p["scene_title"].split()[-3:]) or l.get("visual")
            sc["title"] = play["title"]
    else:
        bible = {} if a.no_llm else storycraft.plan(g, idea, inspo, secs)   # plan a gripping story first
        brief = idea if a.no_llm else "\n".join(x for x in (idea, storycraft.craft(g), storycraft.bible_text(bible), storycraft.rules()) if x)
        sc = write_script(a, g, brief, inspo, secs)
    if not says and not a.no_llm and len(sc["lines"]) > 2:   # punch up vague / repetitive lines (the last line, the CTA or vote, stays)
        body = sc["lines"][:-1]; new = storycraft.punch_up(g, [l["say"] for l in body], bible)
        for l, s in zip(body, new):
            l["say"] = s
    if bible.get("hook") and str(sc.get("title", "")).lower() in ("", str(idea).lower()[:70]):
        sc["title"] = str(bible["hook"])[:70]
    name = time.strftime("%Y%m%d-%H%M") + f"-{a.mode}-{g['name']}-{secs}s-{a.orientation}-" + slug(sc["title"], 28)
    d = str(WORK / name); os.makedirs(d, exist_ok=True)
    json.dump(sc, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    step("3/7 voice");    durs = voice.voice_lines(sc["lines"], d, g)
    gap = None
    if True:   # land close to the length that was picked (speed up or add pauses)
        natural = sum(durs) + timeline.GAP * len(durs) + 1.7
        target = secs if not says or written or abs(natural - secs) <= secs * 0.3 else None   # a custom script keeps its own length if far off
        if says and target is None:
            print(f"  length: your script runs about {natural:.0f}s; keeping that instead of {secs}s")
        durs, gap = voice.fit_length(sc["lines"], durs, d, target, g.get("gap", timeline.GAP))
    step(f"4/7 visuals ({render_visuals.__name__})")
    render_visuals(a, sc, durs, gap, d, g, size)
    if not os.path.exists(os.path.join(d, "video.mp4")):
        sys.exit(f"The {a.mode} renderer did not produce a video. Nothing was uploaded.")
    tl = json.load(open(os.path.join(d, "timeline.json")))
    out = OUTPUT / name; out.mkdir(parents=True, exist_ok=True); final = str(out / "final.mp4")
    step("5/7 music + mix")
    if a.mode in SCREEN_MODES:   # the stick-figure skill's own underscore, ducking and -14 LUFS master
        import scene_sfx, stick_audio, soundfile as sf_, numpy as np_
        timeline._voice_track(d, tl); sf_.write(os.path.join(d, "sfx.wav"), np_.zeros(int((tl["total"] + 1) * 44100), dtype="float32"), 44100)
        scene_sfx.add(d, tl); stick_audio.mix(d, final, tl, g["name"])
    else:
        timeline.music_and_mix(d, final, g, doc=a.mode == "doc", scenes=a.mode == "2d")
    step("6/7 thumbnail"); thumb = thumbnail.make(final, sc.get("thumb_text") or sc["title"], str(out / "thumbnail.jpg"),
                                                  total=tl["total"], color=g.get("thumb_color", "#ffe34a"))
    thumbnail.sheet(final, str(out / "sheet.jpg"), tl["total"])   # quick-review contact sheet with the safe area marked
    meta = {k: sc.get(k) for k in ("title", "description", "tags")}
    meta.update(reference=a.reference or None, custom_script=bool(says), mode=a.mode, renderer=render_visuals.__name__, genre=g["name"], length_s=secs, orientation=a.orientation,
                format="short" if (not land and secs <= 180) else f"{secs}s-{a.orientation}")
    if stock.USED_CREDITS:  # Pexels/Pixabay ask creators to be credited
        meta["description"] = (meta.get("description") or "") + "\n\nFootage: " + "; ".join(stock.USED_CREDITS)
    meta["script"] = [l["say"] for l in sc["lines"]]
    if written:
        (out / "screenplay.txt").write_text(written, encoding="utf-8")
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if a.upload:
        print("7/7 upload"); import upload; meta["youtube_id"] = upload.upload(final, meta, thumb, g)
        json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    else:
        print("7/7 upload skipped (add --upload)")
    print(f"\nDone in {time.time() - t0:.0f}s ({a.mode} via {render_visuals.__name__}) -> {out}")


if __name__ == "__main__":
    main()
