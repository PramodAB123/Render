"""Step 1: find ideas with the free YouTube Data API (search + stats). Falls back to the genre's seed ideas."""
import datetime as dt, json, os, random, sys
import requests
from common import WORK, genre_cfg

API = "https://www.googleapis.com/youtube/v3"


def trending(query, key, days=30, n=15):
    after = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = requests.get(f"{API}/search", params={
        "key": key, "q": query, "part": "snippet", "type": "video", "order": "viewCount",
        "videoDuration": "short", "publishedAfter": after, "relevanceLanguage": "en", "maxResults": n}, timeout=30)
    r.raise_for_status()
    ids = [it["id"]["videoId"] for it in r.json().get("items", [])]
    if not ids:
        return []
    s = requests.get(f"{API}/videos", params={"key": key, "id": ",".join(ids),
                     "part": "snippet,statistics"}, timeout=30).json()
    return [{"title": v["snippet"]["title"], "channel": v["snippet"]["channelTitle"],
             "views": int(v["statistics"].get("viewCount", 0)), "id": v["id"]} for v in s.get("items", [])]


def get_ideas(g):
    key = os.environ.get("YOUTUBE_API_KEY"); found = []
    if key:
        for q in g.get("idea_queries", [g["niche"]]):
            try:
                found += trending(q, key)
            except Exception as e:
                print("  YouTube idea search failed:", e)
    found.sort(key=lambda v: -v["views"])
    WORK.mkdir(exist_ok=True)
    (WORK / f"ideas-{g['name']}.json").write_text(json.dumps(found, indent=1, ensure_ascii=False), encoding="utf-8")
    return found


def pick_idea(g):
    """Returns (idea_text, inspiration_titles). The LLM writes an ORIGINAL video inspired by what trends."""
    found = get_ideas(g); seed = random.choice(g["seed_ideas"])
    if found:
        top = [v["title"] for v in found[:8]]
        print(f"  {len(found)} trending {g['name']} videos found; top: {top[0]!r}")
        return f"{g['niche']} (for example: {seed})", top
    print(f"  no YOUTUBE_API_KEY (or no results) - using a {g['name']} seed idea")
    return seed, []


if __name__ == "__main__":
    for v in get_ideas(genre_cfg(sys.argv[1] if len(sys.argv) > 1 else None))[:20]:
        print(f'{v["views"]:>12,}  {v["title"]}')
