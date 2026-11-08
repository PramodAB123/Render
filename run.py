"""One command: idea -> script -> voice -> visuals -> music -> final.mp4 -> thumbnail -> (optional) YouTube upload.

  python run.py --genre horror            # horror | comedy | science | motivation | mystery | rotate
  python run.py --genre comedy --mode cinema
  python run.py --genre horror --length 5 --mode mix   # 5-minute 16:9 video, AI images + stock clips
  python run.py --idea "your idea"        # skip the YouTube idea search
  python run.py --upload                  # also upload to YouTube (privacy from config.json, default private)
  python run.py --no-llm                  # skip Ollama, use the built-in genre template
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))
from common import load_config, genre_cfg, slug, WORK, OUTPUT  # noqa: E402
import ideas, scriptgen, voice, timeline, stock, cinema, thumbnail, toon, stick, inserts  # noqa: E402


def parse_length(s):
    """'30 sec' -> 30, '1 min' -> 60, '5' -> 300 (bare numbers are minutes), 'short' -> 30."""
    s = str(s).lower().strip()
    if s.startswith("short"):
        return 30
    import re
    n = float(re.match(r"[\d.]+", s).group())
    return int(n) if ("sec" in s or s.endswith("s")) and "min" not in s else int(n * 60)


def main():
    cfg = load_config(); ap = argparse.ArgumentParser()
    ap.add_argument("--genre", default=cfg.get("default_genre", "horror"),
                    help="one of: " + ", ".join(cfg["genres"]) + ", rotate")
    ap.add_argument("--mode", default=cfg.get("mode", "stock"), choices=["stock", "ai", "mix", "doc", "2d", "stick", "cinema"],
                    help="stock clips, AI images, a mix, doc (documentary: AI stills + footage, crossfades, chapter cards), 2d (animated cartoon story), stick (stick-figure explainer), or cinema (3D room, Shorts)")
    ap.add_argument("--length", default="30 sec", help="30 sec, 1 min, 3 min, 5 min or 10 min")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"],
                    help="portrait 9:16 (Shorts / Reels) or landscape 16:9 (normal YouTube video)")
    ap.add_argument("--idea"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--full-quality", action="store_true", help="cinema mode: render 3D at full resolution (slower)")
    a = ap.parse_args(); t0 = time.time(); g = genre_cfg(a.genre)
    secs = parse_length(a.length); minutes = secs / 60; land = a.orientation == "landscape"
    size = cfg["video"]["long_size"] if land else cfg["video"]["size"]
    if a.mode == "cinema" and (land or secs > 60):
        print("  the 3D cinema room is portrait-only and up to 1 min; using mix (AI images + stock) instead"); a.mode = "mix"
    print(f"== genre: {g['name']}  mode: {a.mode}  length: {secs} s  {a.orientation} {size[0]}x{size[1]}")

    step = lambda s: print(f"{s}   [{(time.time() - t0) / 60:.1f} min]", flush=True)
    step("1/7 idea");     idea, inspo = (a.idea, []) if a.idea else ideas.pick_idea(g)
    step("2/7 script")
    if a.mode == "2d":
        sc = toon.write_story(g, idea, inspo, minutes)
    elif a.mode == "stick":
        sc = stick.write_story(g, idea, inspo, secs)
    else:
        sc = (scriptgen.write_long(g, idea, inspo, minutes, use_llm=not a.no_llm, doc=a.mode == "doc") if secs >= 60
              else scriptgen.write_script(g, idea, inspo, use_llm=not a.no_llm))
    name = time.strftime("%Y%m%d-%H%M") + f"-{g['name']}-{secs}s-{a.orientation}-" + slug(sc["title"], 32); d = str(WORK / name); os.makedirs(d, exist_ok=True)
    json.dump(sc, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    step("3/7 voice");    durs = voice.voice_lines(sc["lines"], d, g)
    gap = None
    if a.mode != "cinema":   # land close to the length that was picked (speed up or add pauses)
        durs, gap = voice.fit_length(sc["lines"], durs, d, secs, g.get("gap", timeline.GAP))
    step(f"4/7 visuals ({a.mode})")
    if a.mode == "cinema":
        cinema.render(sc, d, g, fast=not a.full_quality)
    elif a.mode == "2d":
        tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap); toon.render(sc, tl, d, g, size)
    elif a.mode == "stick":
        tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap); stick.render(sc, tl, d, g, size)
    else:
        tl = timeline.build_timeline(sc["lines"], durs, d, g, gap=gap)
        timeline.write_ass(tl, os.path.join(d, "captions.ass"), g, size); stock.render(tl, d, g, size, a.mode)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    if a.mode in ("2d", "stick"):
        inserts.apply(tl, d, g, size)   # /breakdown 3D exploded-view cutaways
    out = OUTPUT / name; out.mkdir(parents=True, exist_ok=True); final = str(out / "final.mp4")
    step("5/7 music + mix"); timeline.music_and_mix(d, final, g, doc=a.mode == "doc")
    step("6/7 thumbnail"); thumb = thumbnail.make(final, sc.get("thumb_text") or sc["title"], str(out / "thumbnail.jpg"),
                                                  total=tl["total"], color=g.get("thumb_color", "#ffe34a"))
    thumbnail.sheet(final, str(out / "sheet.jpg"), tl["total"])   # quick-review contact sheet with the safe area marked
    meta = {k: sc.get(k) for k in ("title", "description", "tags")}; meta["genre"] = g["name"]; meta["format"] = "short" if (not land and secs <= 180) else f"{secs}s-{a.orientation}"
    if stock.USED_CREDITS:  # Pexels/Pixabay ask creators to be credited
        meta["description"] = (meta.get("description") or "") + "\n\nFootage: " + "; ".join(stock.USED_CREDITS)
    meta["script"] = [l["say"] for l in sc["lines"]]
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if a.upload:
        print("7/7 upload"); import upload; meta["youtube_id"] = upload.upload(final, meta, thumb, g)
        json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    else:
        print("7/7 upload skipped (add --upload)")
    print(f"\nDone in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
