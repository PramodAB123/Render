"""Design / animation model chain (free tiers only): Gemini -> Groq -> local Ollama.
Used for designing objects, creatures, characters and motion (pipeline/makers.py, design_people below).
Script writing stays on the local Ollama model (screenwriter.py, storycraft.py ...).

- Gemini: GEMINI_API_KEY (Google AI Studio free tier, no billing). Model: GEMINI_MODEL, default gemini-2.5-flash.
- Groq:   GROQ_API_KEY (free tier). Model: GROQ_MODEL, default llama-3.3-70b-versatile.
- Ollama: the model already running on the runner (LLM_MODEL).
A provider that answers 429 (rate limit / quota) or keeps failing is skipped for the rest of the run, so one
video never waits on a limit; the next provider takes over."""
import json, os, re, time, requests
from common import load_config

_down = {}          # provider -> reason it was switched off for this run
USED = {}           # provider -> number of answers (printed in the log)


def _json(text):
    text = str(text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    i, j = text.find("{"), text.rfind("}")
    return json.loads(text[i:j + 1] if i >= 0 and j > i else text)


def _gemini(prompt, want_json, temp):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LookupError("no GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temp, "maxOutputTokens": 8192}}
    if want_json:
        body["generationConfig"]["responseMimeType"] = "application/json"
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", params={"key": key}, json=body, timeout=180)
    if r.status_code == 429:
        raise PermissionError("Gemini rate limit / free quota reached")
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _groq(prompt, want_json, temp):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise LookupError("no GROQ_API_KEY")
    body = {"model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"), "messages": [{"role": "user", "content": prompt}], "temperature": temp, "max_tokens": 8000}
    if want_json:
        body["response_format"] = {"type": "json_object"}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=180)
    if r.status_code == 429:
        raise PermissionError("Groq rate limit reached")
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _ollama(prompt, want_json, temp):
    c = load_config()["llm"]
    body = {"model": os.environ.get("LLM_MODEL", c["model"]), "prompt": prompt, "stream": False, "options": {"temperature": temp, "num_ctx": 6144, "num_predict": 3000}}
    if want_json:
        body["format"] = "json"
    r = requests.post(f'{c["host"]}/api/generate', json=body, timeout=900)
    r.raise_for_status()
    return r.json()["response"]


CHAIN = [("gemini", _gemini), ("groq", _groq), ("ollama", _ollama)]


def ask(prompt, want_json=True, temp=.5, task="design"):
    """First provider that answers wins. Returns parsed JSON (want_json) or text. Raises if all fail."""
    errors = []
    for name, fn in CHAIN:
        if name in _down:
            continue
        for attempt in range(2):
            try:
                out = fn(prompt, want_json, temp)
                res = _json(out) if want_json else out
                USED[name] = USED.get(name, 0) + 1
                if USED[name] == 1:
                    print(f"  {task}: using {name}", flush=True)
                return res
            except LookupError as e:           # no key: skip quietly
                _down[name] = str(e); break
            except PermissionError as e:       # rate limit: switch to the next provider for the rest of the run
                _down[name] = str(e); print(f"  {task}: {e} -> next model", flush=True); break
            except Exception as e:             # network hiccup / bad JSON: one retry, then move on
                errors.append(f"{name}: {type(e).__name__}")
                if attempt == 0:
                    time.sleep(2); continue
                if name != "ollama":
                    _down[name] = f"{type(e).__name__}"
                print(f"  {task}: {name} failed ({type(e).__name__}) -> next model", flush=True)
    raise RuntimeError("no design model answered (" + "; ".join(errors or list(_down.values())) + ")")


def summary():
    return ", ".join(f"{k} x{v}" for k, v in USED.items()) or "none"


# ------------------------------------------------------------------ character design (people the script names)
PEOPLE_PROMPT = """You design the look of cartoon characters for an animated video. For each character below, from the script's own words,
choose what they wear and carry. Reply JSON only:
{{"people": [{{"name": "...", "hat": "none|crown|helmet|hood|wizard|cap|bandana|sailor|captain|tophat|cowboy|turban|chef",
  "shirt": "#rrggbb", "pants": "#rrggbb", "armour": "none|vest|chainmail|plate", "extras": ["beard","glasses","eyepatch","cape","mustache","scar","hair"],
  "holds": "none|sword|spear|shield|bow|hammer|staff|lantern|map|book|phone|gun", "build": "thin|normal|big", "skin": "#rrggbb"}}]}}
Characters and what the script says about them:
{who}"""


def design_people(entries):
    """entries: [{"name", "text"}] -> {name: look} (empty if no model answers; callers keep their rule-based look)."""
    if not entries:
        return {}
    try:
        res = ask(PEOPLE_PROMPT.format(who="\n".join(f"- {e['name']}: {e['text'][:300]}" for e in entries[:12])), task="character design")
        return {str(p.get("name", "")).lower(): p for p in res.get("people", []) if isinstance(p, dict)}
    except Exception as e:
        print(f"  character design: no model answered ({str(e)[:80]}); using the script-word rules", flush=True)
        return {}
