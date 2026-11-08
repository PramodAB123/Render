"""Step 1: find ideas with the free YouTube Data API (search + stats). Falls back to seed ideas."""
import datetime as dt, json, os, random
import requests
from common import load_config, WORK

API = "https://www.googleapis.com/youtube/v3"


def trending(query, key, days=30, n=15):
    after = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = requests.get(f"{API}/search", params={
        "key": key, "q": query, "part": "snippet", "type": "video", "order": "viewCount",
        "videoDuration": "short", "publishedAfter": after, "maxResults": n}, timeout=30)
    r.raise_for_status()
    ids = [it["id"]["videoId"] for it in r.json().get("items", [])]
    if not ids:
        return []
    s = requests.get(f"{API}/videos", params={"key": key, "id": ",".join(ids),
                     "part": "snippet,statistics"}, timeout=30).json()
    return [{"title": v["snippet"]["title"], "channel": v["snippet"]["channelTitle"],
             "views": int(v["statistics"].get("viewCount", 0)), "id": v["id"]} for v in s.get("items", [])]


def get_ideas():
    cfg = load_config(); key = os.environ.get("YOUTUBE_API_KEY")
    found = []
    if key:
        for q in cfg.get("idea_queries", [cfg["niche"]]):
            try:
                found += trending(q, key)
            except Exception as e:
                print("  YouTube idea search failed:", e)
    found.sort(key=lambda v: -v["views"])
    WORK.mkdir(exist_ok=True)
    (WORK / "ideas.json").write_text(json.dumps(found, indent=1, ensure_ascii=False), encoding="utf-8")
    return found


def pick_idea():
    """Returns (idea_text, inspiration_titles). The LLM writes an ORIGINAL story inspired by what trends."""
    cfg = load_config(); found = get_ideas()
    if found:
        top = [v["title"] for v in found[:8]]
        print(f"  {len(found)} trending videos found; top: {top[0]!r}")
        return cfg["niche"], top
    print("  no YOUTUBE_API_KEY (or no results) - using a seed idea from config.json")
    return random.choice(cfg["seed_ideas"]), []


if __name__ == "__main__":
    for v in get_ideas()[:20]:
        print(f'{v["views"]:>12,}  {v["title"]}')
