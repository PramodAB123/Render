"""Story craft shared by every script writer: plan a gripping story first, then write it, then punch up weak lines.

Why: a small local model asked for "a scary story" writes vague, repetitive lines ("the darkness is coming...").
Planning a concrete story bible first (named hero, exact place, ticking clock, escalating beats, a twist) and
then rewriting any vague line makes the stories specific, surprising and worth finishing."""
import json, os, re
import requests
from common import load_config

# How each genre hooks and holds attention (used in the planning and writing prompts)
CRAFT = {
    "horror": "Horror that works: an ordinary person, a precise place and time, and ONE wrong detail that gets worse. "
              "Use rules (\"never answer after 3 AM\"), evidence (photos, recordings, footprints), a countdown, and a twist "
              "that recontextualises everything (the call is coming from inside, the rescuer is the threat, the hero is the ghost). "
              "Show, don't name: never say 'darkness', 'evil' or 'something'; say what is seen and heard.",
    "mystery": "Mystery that works: a strange true-feeling event with exact dates, places and numbers, clues revealed one at a time, "
               "a red herring, then the detail nobody noticed. End on the open question viewers will argue about.",
    "comedy": "Comedy that works: a relatable situation, escalation in three steps where each step is worse and more specific, "
              "a callback to the first line, and a twist punchline. Specific beats generic every time.",
    "science": "Science that works: open with the surprising fact or a 'what if', bust the common belief, explain the real mechanism "
               "with one vivid comparison, add one number that shocks, end with the mind-blowing implication.",
    "motivation": "Motivation that works: a real-feeling person at their lowest point with concrete details (time, place, money, pain), "
                  "the moment they choose differently, the cost, the result, then one line the viewer can use today.",
    "history": "History that works: drop into one exact moment (date, place, weather, who), the stakes for real people, "
               "the decision that changed everything, the detail most people never learn, and what it means now.",
}
BANNED = ["darkness", "something", "somehow", "suddenly", "mysterious", "evil", "a presence", "strange feeling", "eerie silence",
          "little did", "unknown", "it is coming", "they are coming", "no one knows", "the end"]

BIBLE = """Plan a short {genre} video story ({seconds} seconds, about {words} spoken words). {craft}
Idea to start from: {idea}
{inspo}
Make it ORIGINAL and specific. Reply with JSON only:
{{"hook": "first spoken line: an impossible fact, a shocking moment already happening, or a direct question to the viewer (max 12 words)",
  "hero": "name, age, job/role and one telling detail",
  "place": "exact place and time (e.g. 'Mile 41 rest stop, Route 50, 2:14 AM')",
  "want": "what the hero needs right now",
  "clock": "the ticking clock or deadline",
  "beats": ["escalation 1 with a concrete detail", "escalation 2, worse", "escalation 3, worst"],
  "twist": "the reveal that changes what we thought was happening",
  "ending": "the final line: a cliffhanger or a question viewers will answer in the comments"}}"""

RULES = """Writing rules (follow all):
- Line 1 is the hook. Every line adds NEW information; never repeat an idea.
- Concrete beats vague: names, numbers, times, brands of objects, sounds, smells. Short punchy sentences.
- No ellipses (...). Never use these words: {banned}.
- Rising tension every line, the twist about two thirds of the way in, and the ending as planned."""

PUNCH = """Here are the spoken lines of a {genre} video. Some are vague, repetitive or boring.
Story plan: {bible}
Rewrite EVERY line to be specific, vivid and gripping, keeping the same order, meaning and roughly the same length (6-18 words each).
{rules}
Lines:
{numbered}
Reply with JSON only: {{"lines": ["line 1", "line 2", ...]}} with exactly {n} lines."""


def _ollama(prompt, n=1500, temp=0.9):
    c = load_config()["llm"]
    r = requests.post(f'{c["host"]}/api/generate', json={"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt, "format": "json",
                      "stream": False, "options": {"temperature": temp, "num_ctx": 4096, "num_predict": n, "repeat_penalty": 1.15}}, timeout=1200)
    r.raise_for_status()
    return json.loads(r.json()["response"])


def craft(g):
    return CRAFT.get(g["name"], CRAFT["horror"])


def rules():
    return RULES.format(banned=", ".join(BANNED))


def plan(g, idea, inspo, seconds):
    """A story bible (dict) the writers follow; {} if the model fails (writers still work without it)."""
    ins = ("Popular videos on this topic (tone only, never copy): " + " | ".join(inspo[:6])) if inspo else ""
    for attempt in range(2):
        try:
            b = _ollama(BIBLE.format(genre=g["name"], seconds=seconds, words=int(seconds * 2.75), craft=craft(g), idea=idea, inspo=ins))
            if b.get("hook") and b.get("beats"):
                print(f"  story plan: {str(b.get('hook'))[:70]!r} | twist: {str(b.get('twist'))[:60]!r}")
                return b
        except Exception as e:
            print(f"  story plan retry ({type(e).__name__})")
    return {}


def bible_text(b):
    if not b:
        return ""
    beats = " / ".join(str(x) for x in (b.get("beats") or []))
    return (f"STORY PLAN (follow it): hook: {b.get('hook')} | hero: {b.get('hero')} | place: {b.get('place')} | wants: {b.get('want')} | "
            f"clock: {b.get('clock')} | beats: {beats} | twist: {b.get('twist')} | ending: {b.get('ending')}")


def weak(lines):
    """How boring the script looks: vague words, ellipses, repeated openings, too few concrete details."""
    txt = [str(x) for x in lines]; low = " ".join(txt).lower(); n = max(1, len(txt))
    vague = sum(low.count(w) for w in BANNED) + low.count("...") + low.count("…")
    starts = [" ".join(t.lower().split()[:2]) for t in txt]; repeats = len(starts) - len(set(starts))
    concrete = sum(1 for t in txt if re.search(r"\d|[A-Z][a-z]+ [A-Z]|[A-Z][a-z]{2,}", t[1:] if t else ""))
    return vague + repeats + max(0, n // 2 - concrete)


def punch_up(g, says, bible=None):
    """Rewrite weak lines (same count and order). Returns the new list, or the original if it can't improve it."""
    if not says or weak(says) <= 1:
        return says
    before = weak(says)
    for attempt in range(2):
        try:
            out = _ollama(PUNCH.format(genre=g["name"], bible=bible_text(bible) or "(none)", rules=rules(), n=len(says),
                                       numbered="\n".join(f"{i + 1}. {s}" for i, s in enumerate(says))), 2200, 0.8).get("lines", [])
            out = [re.sub(r"\s+", " ", str(x)).strip().strip('"').replace("...", ".").replace("…", ".") for x in out]
            out = [re.sub(r"^\d+[.)]\s*", "", x) for x in out]
            if len(out) == len(says) and all(len(x.split()) >= 3 for x in out) and weak(out) < before:
                print(f"  punch-up: weak score {before} -> {weak(out)}")
                return out
        except Exception as e:
            print(f"  punch-up retry ({type(e).__name__})")
    return [s.replace("...", ".").replace("…", ".") for s in says]
