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
import ideas, scriptgen, voice, timeline, stock, cinema, thumbnail, toon, stick, reference  # noqa: E402


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


def render_cinema(a, sc, durs, gap, d, g, size):
    cinema.render(sc, d, g, fast=not a.full_quality)


MODES = {
    #  mode      script writer       renderer         what it is
    "stock":  (script_narration, render_footage, "free Pixabay/Pexels clips + word-timed captions"),
    "ai":     (script_narration, render_footage, "AI images (DreamShaper LCM on the runner) with camera moves"),
    "mix":    (script_narration, render_footage, "AI images and stock clips, alternating"),
    "doc":    (script_narration, render_footage, "documentary: AI stills + footage, crossfades, chapter cards"),
    "2d":     (script_toon,      render_toon,    "2D flat-vector cartoon (toon/toon.html, GSAP)"),
    "stick":  (script_stick,     render_stick,   "stick-figure engine from claude-animation-skills (stick/auto_shots.js)"),
    "cinema": (script_narration, render_cinema,  "3D code-cinema room (portrait, up to 1 min)"),
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
    ap.add_argument("--genre", default=cfg.get("default_genre", "horror"), help="one of: " + ", ".join(cfg["genres"]) + ", rotate")
    ap.add_argument("--mode", default=cfg.get("mode", "stock"), help="; ".join(f"{k}: {v[2]}" for k, v in MODES.items()))
    ap.add_argument("--length", default="30 sec", help="30 sec, 1 min, 3 min, 5 min or 10 min")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"],
                    help="portrait 9:16 (Shorts / Reels) or landscape 16:9 (normal YouTube video)")
    ap.add_argument("--reference", help="optional link (YouTube or any page) to base the idea and tone on")
    ap.add_argument("--idea"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--full-quality", action="store_true", help="cinema mode: render 3D at full resolution (slower)")
    a = ap.parse_args(); t0 = time.time()
    a.mode = str(a.mode).strip().lower()
    if a.mode not in MODES:
        sys.exit(f"Unknown mode {a.mode!r}. Choose one of: {', '.join(MODES)}")
    g = genre_cfg(a.genre); secs = parse_length(a.length); land = a.orientation == "landscape"
    size = cfg["video"]["long_size"] if land else cfg["video"]["size"]
    if a.mode == "cinema" and (land or secs > 60):
        sys.exit("cinema mode is portrait-only and up to 1 min. Pick portrait + 30 sec / 1 min, or another mode.")
    write_script, render_visuals, what = MODES[a.mode]
    print(f"== mode: {a.mode} ({what})\n== genre: {g['name']}  length: {secs} s  {a.orientation} {size[0]}x{size[1]}", flush=True)

    step = lambda s: print(f"{s}   [{(time.time() - t0) / 60:.1f} min]", flush=True)
    step("1/7 idea")
    if reference.is_link(a.idea) and not a.reference:   # a link pasted into the idea box counts as a reference
        a.reference, a.idea = a.idea.strip(), None
    ref = reference.read(a.reference) if a.reference else None
    if ref:
        idea, inspo = reference.to_idea(ref, a.idea), [ref["title"]]
    else:
        idea, inspo = (a.idea, []) if a.idea else ideas.pick_idea(g)
    step(f"2/7 script ({write_script.__name__})")
    sc = write_script(a, g, idea, inspo, secs)
    name = time.strftime("%Y%m%d-%H%M") + f"-{a.mode}-{g['name']}-{secs}s-{a.orientation}-" + slug(sc["title"], 28)
    d = str(WORK / name); os.makedirs(d, exist_ok=True)
    json.dump(sc, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    step("3/7 voice");    durs = voice.voice_lines(sc["lines"], d, g)
    gap = None
    if a.mode != "cinema":   # land close to the length that was picked (speed up or add pauses)
        durs, gap = voice.fit_length(sc["lines"], durs, d, secs, g.get("gap", timeline.GAP))
    step(f"4/7 visuals ({render_visuals.__name__})")
    render_visuals(a, sc, durs, gap, d, g, size)
    if not os.path.exists(os.path.join(d, "video.mp4")):
        sys.exit(f"The {a.mode} renderer did not produce a video. Nothing was uploaded.")
    tl = json.load(open(os.path.join(d, "timeline.json")))
    out = OUTPUT / name; out.mkdir(parents=True, exist_ok=True); final = str(out / "final.mp4")
    step("5/7 music + mix"); timeline.music_and_mix(d, final, g, doc=a.mode == "doc")
    step("6/7 thumbnail"); thumb = thumbnail.make(final, sc.get("thumb_text") or sc["title"], str(out / "thumbnail.jpg"),
                                                  total=tl["total"], color=g.get("thumb_color", "#ffe34a"))
    thumbnail.sheet(final, str(out / "sheet.jpg"), tl["total"])   # quick-review contact sheet with the safe area marked
    meta = {k: sc.get(k) for k in ("title", "description", "tags")}
    meta.update(reference=a.reference or None, mode=a.mode, renderer=render_visuals.__name__, genre=g["name"], length_s=secs, orientation=a.orientation,
                format="short" if (not land and secs <= 180) else f"{secs}s-{a.orientation}")
    if stock.USED_CREDITS:  # Pexels/Pixabay ask creators to be credited
        meta["description"] = (meta.get("description") or "") + "\n\nFootage: " + "; ".join(stock.USED_CREDITS)
    meta["script"] = [l["say"] for l in sc["lines"]]
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if a.upload:
        print("7/7 upload"); import upload; meta["youtube_id"] = upload.upload(final, meta, thumb, g)
        json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    else:
        print("7/7 upload skipped (add --upload)")
    print(f"\nDone in {time.time() - t0:.0f}s ({a.mode} via {render_visuals.__name__}) -> {out}")


if __name__ == "__main__":
    main()
