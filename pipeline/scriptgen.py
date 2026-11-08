"""Step 2: write the script with a free local LLM (Ollama) in the genre's style. Falls back to a genre template."""
import json, os
import requests
from common import load_config

PROMPT = """You write viral 25-35 second vertical YouTube Shorts. Genre: {genre}. Niche: {niche}.
Style: {tone}
Write ONE completely original video (never copy an existing video or story).
Starting idea: {idea}
{inspo}
Rules: line 1 is a scroll-stopping hook under 10 words. 7 to 10 lines total, each 4-14 words.
The last line ends with exactly: "{cta}"
For every line give a 2-3 word stock-footage search ("visual") that matches the genre: {visual_hint}.
Reply with JSON only, exactly this shape:
{{"title": "under 70 chars, curiosity title", "description": "2 sentences", "tags": ["5-10 tags"],
  "thumb_text": "2-4 WORDS", "lines": [{{"say": "...", "visual": "2-3 words", "hl": "one key word from say"}}]}}"""

FALLBACK = {
    "horror": ["You have ten seconds to decide.", "{idea}.", "Everything goes quiet. Too quiet.",
               "Then you hear it again. Closer.", "Your phone has one bar of battery left.",
               "Do you hide, or do you run?"],
    "comedy": ["Nobody talks about this, but everyone does it.", "{idea}.", "Step one: act completely normal.",
               "Step two: panic, but quietly.", "Step three: blame the dog.", "And somehow it still works every time."],
    "science": ["Here is something your brain will not believe.", "{idea}.", "Scientists have studied this for decades.",
                "The answer is stranger than you think.", "It changes how you see everything around you.",
                "And it is happening right now."],
    "motivation": ["Listen. This is for you.", "{idea}.", "Every day you wait, the gap gets bigger.",
                   "Nobody sees the work you do in the dark.", "But one day, everyone sees the results.",
                   "Start today. Not Monday. Today."],
    "mystery": ["This has never been explained.", "{idea}.", "Witnesses reportedly saw nothing unusual.",
                "But one detail does not add up.", "Investigators reportedly closed the case without answers.",
                "So what really happened?"],
}


def from_ollama(g, idea, inspo):
    cfg = load_config()["llm"]
    ins = ("Trending titles right now (for tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
    r = requests.post(f'{cfg["host"]}/api/generate', json={
        "model": os.environ.get("LLM_MODEL", cfg["model"]),
        "prompt": PROMPT.format(genre=g["name"], niche=g["niche"], tone=g["tone"], idea=idea, inspo=ins,
                                cta=g["cta"], visual_hint=g["visual_hint"]),
        "format": "json", "stream": False, "options": {"temperature": 0.9}}, timeout=600)
    r.raise_for_status()
    data = json.loads(r.json()["response"])
    lines = [l for l in data.get("lines", []) if isinstance(l, dict) and l.get("say")]
    if len(lines) < 4:
        raise ValueError("LLM returned too few lines")
    data["lines"] = lines
    return data


def fallback(g, idea):
    if "(for example: " in idea:
        idea = idea.split("(for example: ", 1)[1].rstrip(")")
    text = [t.format(idea=idea.rstrip(".")) for t in FALLBACK.get(g["name"], FALLBACK["horror"])] + [g["cta"]]
    words = g["visual_hint"].split('"')
    examples = [words[i] for i in range(1, len(words), 2)] or [g["visual_style"]]
    lines = [{"say": t, "visual": examples[i % len(examples)], "hl": max(t.split(), key=len).strip(".,?!")}
             for i, t in enumerate(text)]
    return {"title": idea[:70], "description": idea, "tags": [], "thumb_text": " ".join(idea.split()[:3]).upper(), "lines": lines}


# ---------------- long-form (1-10 minute, 16:9) ----------------
OUTLINE = """You plan a {minutes}-minute narrated YouTube video. Genre: {genre}. Niche: {niche}.
Style: {tone}
Write ONE completely original story/topic (never copy an existing video). Starting idea: {idea}
{inspo}
Split it into exactly {chapters} chapters that build to a strong ending.
Reply with JSON only:
{{"title": "under 70 chars, curiosity title", "description": "3 sentences", "tags": ["8-12 tags"],
  "thumb_text": "2-4 WORDS", "chapters": [{{"heading": "...", "summary": "2 sentences of what happens"}}]}}"""

CHAPTER = """You are the narrator of a {minutes}-minute {genre} YouTube video titled "{title}".
Style: {tone}
Story plan: {plan}
Write chapter {n} of {total}: "{heading}" - {summary}
{prev}
Write AT LEAST {words} words of spoken narration for this chapter. Use vivid, concrete details, short paragraphs,
and keep the story moving. {extra}
Write only the narration text itself: no headings, no labels, no lists, no stage directions."""

MORE = """Continue the narration of chapter {n} ("{heading}") directly from where it stops below. Add about {words} more words
in the same voice and style, moving the chapter forward. Write only narration text, nothing else.

Narration so far:
{text}"""

VISUALS = """For each numbered narration line of a {genre} video, give footage ideas.
"visual": a 2-3 word stock-footage search ({visual_hint}).
"image": one vivid sentence describing the scene for an AI image generator (subject, setting, lighting, camera angle; no text).
"hl": the single most important word of that line.
Lines:
{numbered}
Reply with JSON only: {{"scenes": [{{"n": 1, "visual": "...", "image": "...", "hl": "..."}}]}} with exactly {count} scenes."""

WPM = 150  # narration speed (words per minute)


def _ollama(prompt, num_predict=2048, as_json=True):
    cfg = load_config()["llm"]
    body = {"model": os.environ.get("LLM_MODEL", cfg["model"]), "prompt": prompt, "stream": False,
            "options": {"temperature": 0.85, "num_ctx": 4096, "num_predict": num_predict, "repeat_penalty": 1.1}}
    if as_json:
        body["format"] = "json"
    r = requests.post(f'{cfg["host"]}/api/generate', json=body, timeout=1800)
    r.raise_for_status()
    out = r.json()["response"]
    return json.loads(out) if as_json else out.strip()


LABELS = ("chapter", "narrator", "title", "here is", "here's", "(", "[")


def _clean(text):
    """Drop headings/labels the model sometimes adds; keep plain narration."""
    keep = []
    for ln in text.replace("\r", "").split("\n"):
        t = ln.strip().strip("*#").strip()
        if not t or (t.lower().startswith(LABELS) and len(t.split()) < 8):
            continue
        keep.append(t.strip('"'))
    return " ".join(keep)


def _trim(text, max_words):
    """Cut to at most max_words, ending on a full sentence."""
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words]); end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[:end + 1] if end > len(cut) // 2 else cut


def _to_lines(text, lo=10, hi=24):
    """Split narration into spoken lines of roughly 10-24 words (one scene each)."""
    import re
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
    pieces = []
    for st in sents:   # break very long sentences at commas/semicolons
        w = st.split()
        while len(w) > hi:
            cut = next((i + 1 for i in range(hi - 1, lo - 1, -1) if w[i].endswith((",", ";", ":"))), hi)
            pieces.append(" ".join(w[:cut])); w = w[cut:]
        if w:
            pieces.append(" ".join(w))
    lines, cur = [], []
    for pc in pieces:  # merge very short sentences
        cur += pc.split()
        if len(cur) >= lo:
            lines.append(" ".join(cur)); cur = []
    if cur:
        if lines and len(cur) < lo // 2:
            lines[-1] += " " + " ".join(cur)
        else:
            lines.append(" ".join(cur))
    return lines


def _visuals(g, lines):
    """Ask the LLM for clip searches + image prompts in batches; fill gaps with simple keywords."""
    out = [None] * len(lines)
    for b0 in range(0, len(lines), 10):
        batch = lines[b0:b0 + 10]
        try:
            res = _ollama(VISUALS.format(genre=g["name"], visual_hint=g["visual_hint"], count=len(batch),
                                         numbered="\n".join(f"{i + 1}. {t}" for i, t in enumerate(batch))), 1500)
            for i, sc in enumerate([x for x in res.get("scenes", []) if isinstance(x, dict)][:len(batch)]):
                out[b0 + i] = sc
        except Exception as e:
            print(f"  visuals batch {b0 // 10 + 1} fell back to keywords ({e})")
    result = []
    for t, sc in zip(lines, out):
        sc = sc or {}
        words = [w.strip(".,!?;:\"'").lower() for w in t.split()]
        key = " ".join(sorted((w for w in words if len(w) > 4), key=len, reverse=True)[:2]) or g["visual_style"]
        result.append({"say": t, "visual": sc.get("visual") or key, "image": sc.get("image") or t,
                       "hl": sc.get("hl") or max(t.split(), key=len).strip(".,!?")})
    return result


DOC_TONE = (" Documentary narration: a calm, authoritative narrator, vivid scene-setting, concrete details, "
            "dates and places where they fit, building suspense chapter by chapter.")


def write_long(g, idea, inspo, minutes, use_llm=True, doc=False):
    if not use_llm:
        raise SystemExit("Long videos need the Ollama script writer (remove --no-llm).")
    chapters = max(3, min(8, round(minutes * 0.8)))   # fewer, longer chapters = fewer slow LLM calls
    if doc:
        g = dict(g, tone=g["tone"] + DOC_TONE)
    words_total = int(minutes * WPM); target = max(60, words_total // chapters)
    ins = ("Trending titles (tone only, do not copy):\n- " + "\n- ".join(inspo)) if inspo else ""
    plan, chs = {}, []
    for attempt in range(3):
        try:
            plan = _ollama(OUTLINE.format(minutes=minutes, genre=g["name"], niche=g["niche"], tone=g["tone"], idea=idea,
                                          inspo=ins, chapters=chapters), 1500)
            chs = [c for c in plan.get("chapters", []) if isinstance(c, dict) and c.get("heading")][:chapters]
            if len(chs) >= 2:
                break
        except Exception as e:
            print(f"  outline retry ({e})")
    if len(chs) < 2:   # still make the video: simple chapter plan from the idea
        plan = {"title": idea[:70], "description": idea, "tags": [], "thumb_text": " ".join(idea.split()[:3]).upper()}
        chs = [{"heading": h, "summary": idea} for h in ("The beginning", "It gets worse", "The truth", "The ending")]
    print(f"  outline: {plan.get('title')!r}, {len(chs)} chapters, aiming for ~{words_total} words")
    plan_txt = " | ".join(f"{i + 1}. {c['heading']}: {c.get('summary', '')}" for i, c in enumerate(chs))
    story = []
    for n, c in enumerate(chs, 1):
        extra = ("Open with a gripping hook sentence. " if n == 1 else "") + \
                (f'End the chapter with this exact sentence: "{g["cta"]}"' if n == len(chs) else "")
        prev = ("The story so far ends with: " + " ".join(story[-1].split()[-60:])) if story else ""
        text = ""
        for attempt in range(3):   # write, then extend (max 2 times) until the chapter is long enough
            try:
                if not text:
                    text = _clean(_ollama(CHAPTER.format(minutes=minutes, genre=g["name"], title=plan.get("title", idea),
                                                         tone=g["tone"], plan=plan_txt, n=n, total=len(chs), heading=c["heading"],
                                                         summary=c.get("summary", ""), prev=prev, words=target, extra=extra),
                                          int(target * 2.2) + 200, as_json=False))
                else:
                    more = _clean(_ollama(MORE.format(n=n, heading=c["heading"], words=target - len(text.split()), text=text),
                                          int(target * 2) + 200, as_json=False))
                    text = (text + " " + more).strip()
            except Exception as e:
                print(f"  chapter {n} retry ({e})")
            if len(text.split()) >= target * 0.75:
                break
        text = _trim(text, int(target * 1.25))  # don't overshoot the length
        if n == len(chs) and g["cta"].lower().rstrip(".") not in text.lower():
            text = (text + " " + g["cta"]).strip()
        story.append(text)
        print(f"  chapter {n}/{len(chs)}: {c['heading']}  ({len(text.split())} words, total {sum(len(t.split()) for t in story)})")
    lines, heads = [], []   # ~10-15 s per scene; remember where each chapter starts (title cards)
    for c, text in zip(chs, story):
        part = _to_lines(text, lo=22, hi=40)
        heads += [c["heading"]] + [None] * (len(part) - 1); lines += part
    got = sum(len(l.split()) for l in lines)
    if got < words_total * 0.6:
        print(f"  note: script is {got} words (~{got / WPM:.1f} min), shorter than the {minutes:g} min asked; making it anyway")
    if not lines:
        raise SystemExit("The script writer returned nothing (is Ollama running?). Nothing was uploaded. Please run again.")
    print(f"  {len(lines)} scenes; adding clip searches and image prompts")
    plan["lines"] = _visuals(g, lines)
    for ln, h in zip(plan["lines"], heads):
        if h:
            ln["chapter"] = h
    return plan


def write_script(g, idea, inspo, use_llm=True):
    if use_llm:
        try:
            s = from_ollama(g, idea, inspo); print("  script written by Ollama:", s["title"]); return s
        except Exception as e:
            print("  Ollama not available or failed (", e, ") - using the built-in template")
    return fallback(g, idea)
