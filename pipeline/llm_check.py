"""One tiny request to each design model, so the run log shows whether the Gemini and Groq keys work.
Prints only OK / the error type - never the keys."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import llm

for name, fn in llm.CHAIN[:2]:
    env = "GEMINI_API_KEY" if name == "gemini" else "GROQ_API_KEY"
    if not os.environ.get(env):
        print(f"{name}: no {env} secret - skipped (Ollama will do its jobs)"); continue
    try:
        out = llm._json(fn('Reply with JSON only: {"ok": true}', True, 0))
        print(f"{name}: OK ({'ok' in out and out['ok']})")
    except PermissionError as e:
        print(f"{name}: rate limit right now ({e}) - the next model takes over")
    except Exception as e:
        print(f"{name}: FAILED ({type(e).__name__}: {str(e)[:120]})")
