"""Your own script: the narrator says exactly your lines, in your order.
The pipeline only decides what we SEE for each line (scenes, moods, clips, images), never the words.
Separate lines with | or new lines; one long block is split into sentences."""
import re
import scriptgen


def split(text):
    text = str(text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\s*\|\s*|\n+", text) if p.strip()]
    if len(parts) == 1:   # one block: split into spoken lines of a sensible length
        parts = scriptgen._to_lines(parts[0], lo=6, hi=24)
    return [re.sub(r"\s+", " ", p) for p in parts]


def brief(says, extra=None):
    """Instruction for the story writers of 2d / stick: keep these exact lines, only choose the visuals."""
    return ("CUSTOM SCRIPT: use EXACTLY these lines as the \"say\" values, in this order, one entry per line. "
            "Do not add, remove, merge or rewrite any line; only choose the other fields (scene, mood, characters, ...).\n"
            + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(says)) + (f"\nExtra details from the author: {extra}" if extra else ""))


def align(lines, says):
    """Force the writer's lines to be exactly the author's lines (same count and order), keeping its visual choices."""
    if not lines:
        lines = [{}]
    out = []
    for i, s in enumerate(says):
        base = dict(lines[i] if i < len(lines) else lines[i % len(lines)])
        base.pop("words", None); base["say"] = s
        out.append(base)
    return out


def narration(g, says):
    """For stock / ai / mix / doc / cinema: clip searches and image prompts for each of the author's lines."""
    lines = scriptgen._visuals(g, says)
    first = says[0]
    return {"title": first[:70], "description": " ".join(says)[:300], "tags": [], "thumb_text": " ".join(first.split()[:3]).upper(), "lines": lines}
