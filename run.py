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
import ideas, scriptgen, voice, timeline, stock, cinema, thumbnail  # noqa: E402


def main():
    cfg = load_config(); ap = argparse.ArgumentParser()
    ap.add_argument("--genre", default=cfg.get("default_genre", "horror"),
                    help="one of: " + ", ".join(cfg["genres"]) + ", rotate")
    ap.add_argument("--mode", default=cfg.get("mode", "stock"), choices=["stock", "ai", "mix", "cinema"],
                    help="stock clips, AI images, a mix of both, or the 3D cinema room (Shorts only)")
    ap.add_argument("--length", default="short", help="short (vertical Short) or minutes for a 16:9 video: 1, 3, 5, 10")
    ap.add_argument("--idea"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--full-quality", action="store_true", help="cinema mode: render 3D at full resolution (slower)")
    a = ap.parse_args(); t0 = time.time(); g = genre_cfg(a.genre)
    minutes = 0 if str(a.length).lower().startswith("short") else float(str(a.length).split()[0])
    size = cfg["video"]["long_size"] if minutes else cfg["video"]["size"]
    if minutes and a.mode == "cinema":
        print("  the 3D cinema room is vertical-only; using mix (AI images + stock) for this long video"); a.mode = "mix"
    print(f"== genre: {g['name']}  mode: {a.mode}  length: {f'{minutes:g} min (16:9)' if minutes else 'Short (9:16)'}")

    step = lambda s: print(f"{s}   [{(time.time() - t0) / 60:.1f} min]", flush=True)
    step("1/7 idea");     idea, inspo = (a.idea, []) if a.idea else ideas.pick_idea(g)
    step("2/7 script")
    sc = (scriptgen.write_long(g, idea, inspo, minutes, use_llm=not a.no_llm) if minutes
          else scriptgen.write_script(g, idea, inspo, use_llm=not a.no_llm))
    name = time.strftime("%Y%m%d-%H%M") + f"-{g['name']}{f'-{minutes:g}min' if minutes else ''}-" + slug(sc["title"], 32); d = str(WORK / name); os.makedirs(d, exist_ok=True)
    json.dump(sc, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    step("3/7 voice");    durs = voice.voice_lines(sc["lines"], d, g)
    step(f"4/7 visuals ({a.mode})")
    if a.mode == "cinema":
        cinema.render(sc, d, g, fast=not a.full_quality)
    else:
        tl = timeline.build_timeline(sc["lines"], durs, d, g)
        timeline.write_ass(tl, os.path.join(d, "captions.ass"), g, size); stock.render(tl, d, g, size, a.mode)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    out = OUTPUT / name; out.mkdir(parents=True, exist_ok=True); final = str(out / "final.mp4")
    step("5/7 music + mix"); timeline.music_and_mix(d, final, g)
    step("6/7 thumbnail"); thumb = thumbnail.make(final, sc.get("thumb_text") or sc["title"], str(out / "thumbnail.jpg"),
                                                  total=tl["total"], color=g.get("thumb_color", "#ffe34a"))
    meta = {k: sc.get(k) for k in ("title", "description", "tags")}; meta["genre"] = g["name"]; meta["format"] = f"{minutes:g}min" if minutes else "short"
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
