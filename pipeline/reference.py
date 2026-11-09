"""Optional reference link: base the new video's idea and tone on a video or page you like (never a copy).
YouTube links: title, channel, description and tags from the free YouTube Data API (your YOUTUBE_API_KEY).
Any other link: the page title, its description and the first part of its text."""
import html, os, re
import requests

YT_ID = re.compile(r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})")


def _youtube(vid):
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"key": key, "id": vid, "part": "snippet"}, timeout=30)
        items = r.json().get("items", []) if r.ok else []
        if items:
            s = items[0]["snippet"]
            return {"title": s.get("title", ""), "by": s.get("channelTitle", ""), "text": s.get("description", "")[:1500],
                    "tags": s.get("tags", [])[:12]}
    # no key: the public oEmbed endpoint still gives the title and channel
    r = requests.get("https://www.youtube.com/oembed", params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}, timeout=30)
    if r.ok:
        j = r.json(); return {"title": j.get("title", ""), "by": j.get("author_name", ""), "text": "", "tags": []}
    return None


def _page(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; RenderPipeline/1.0)"})
    r.raise_for_status(); h = r.text
    title = re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)
    desc = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\'](.*?)["\']', h, re.S | re.I)
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I); body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", html.unescape(body)).strip()
    return {"title": html.unescape(title.group(1).strip()) if title else url, "by": "", "text": (html.unescape(desc.group(1)) + " " if desc else "") + body[:1200], "tags": []}


def is_link(s):
    return bool(s) and bool(re.match(r"https?://", str(s).strip()))


def read(url):
    """Returns {'title','by','text','tags'} or None. Never raises."""
    try:
        url = url.strip(); m = YT_ID.search(url)
        ref = _youtube(m.group(1)) if m else _page(url)
        if ref:
            print(f"  reference: {ref['title']!r}" + (f" by {ref['by']}" if ref['by'] else ""))
        return ref
    except Exception as e:
        print(f"  reference link could not be read ({type(e).__name__}); continuing without it")
        return None


def to_idea(ref, extra_idea=None):
    """Turn the reference into an idea for the script writers: same kind of story and tone, new content."""
    parts = [f'Make an ORIGINAL video in the same style and topic area as this reference (do not copy its story, names or lines): '
             f'"{ref["title"]}"' + (f' by {ref["by"]}' if ref["by"] else "") + "."]
    if ref.get("text"):
        parts.append("What the reference is about: " + re.sub(r"https?://\S+", "", ref["text"])[:600].strip())
    if ref.get("tags"):
        parts.append("Its keywords: " + ", ".join(ref["tags"]))
    if extra_idea:
        parts.append("My own idea for the new video: " + extra_idea)
    return " ".join(parts)
