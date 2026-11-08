"""One command: idea -> script -> voice -> visuals -> music -> final.mp4 -> thumbnail -> (optional) YouTube upload.

  python run.py                     # full auto, mode from config.json ("stock" or "cinema")
  python run.py --mode cinema       # code-rendered three.js room instead of stock clips
  python run.py --idea "your idea"  # skip the YouTube idea search
  python run.py --upload            # also upload to YouTube (privacy from config.json, default private)
  python run.py --no-llm            # skip Ollama, use the built-in template script
"""
import argparse, json, os, shutil, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))
from common import load_config, slug, WORK, OUTPUT  # noqa: E402
import ideas, scriptgen, voice, timeline, stock, cinema, thumbnail  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); cfg = load_config()
    ap.add_argument("--mode", default=cfg.get("mode", "stock"), choices=["stock", "cinema"])
    ap.add_argument("--idea"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--full-quality", action="store_true", help="cinema mode: render 3D at full resolution (slower)")
    a = ap.parse_args(); t0 = time.time()

    print("1/7 idea");     idea, inspo = (a.idea, []) if a.idea else ideas.pick_idea()
    print("2/7 script");   sc = scriptgen.write_script(idea, inspo, use_llm=not a.no_llm)
    name = time.strftime("%Y%m%d-%H%M") + "-" + slug(sc["title"]); d = str(WORK / name); os.makedirs(d, exist_ok=True)
    json.dump(sc, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("3/7 voice");    durs = voice.voice_lines(sc["lines"], d)
    print(f"4/7 visuals ({a.mode})")
    if a.mode == "cinema":
        cinema.render(sc, d, fast=not a.full_quality)
    else:
        tl = timeline.build_timeline(sc["lines"], durs, d); timeline.write_ass(tl, os.path.join(d, "captions.ass")); stock.render(tl, d)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    out = OUTPUT / name; out.mkdir(parents=True, exist_ok=True); final = str(out / "final.mp4")
    print("5/7 music + mix"); timeline.music_and_mix(d, final)
    print("6/7 thumbnail"); thumb = thumbnail.make(final, sc.get("thumb_text") or sc["title"], str(out / "thumbnail.jpg"), total=tl["total"])
    meta = {k: sc.get(k) for k in ("title", "description", "tags")}; meta["script"] = [l["say"] for l in sc["lines"]]
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if a.upload:
        print("7/7 upload"); import upload; meta["youtube_id"] = upload.upload(final, meta, thumb)
        json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    else:
        print("7/7 upload skipped (add --upload)")
    print(f"\nDone in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
