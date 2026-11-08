---
name: code-cinema
description: Make short vertical "this wasn't made in Blender, every frame is code" Reels - a cinematic three.js retro-room scene with sunlit blinds, camera moves, an on-screen app UI, word-by-word captions, voiceover, lofi music and a 3D "Comment WORD" end card - from one script.json.
---

# Code Cinema: cinematic code-rendered Reels

Turns a short script into a 9:16 Reel (1080x1920, 30 fps, 20-35 s) in the style of the
"This wasn't made in Blender" reference: a warm, golden-hour 3D room (beige retro computer,
red-brown desk, venetian-blind shadow stripes, light shafts, dust, desk lamp, plant, mug, phone),
slow cinematic camera moves, bold white captions that pop in word by word, a retro app on the
monitor, a grey "bad version" vs. the golden "good version", and a 3D extruded CTA word.
Every frame is rendered in code (three.js in headless Chromium, captured to ffmpeg).

## What the reference does (the style rules)

| Element | Rule |
|---|---|
| Format | Vertical 9:16, ~30 s, hard cuts every 1.5-3.5 s, one shot per line |
| Hook (0-3 s) | Bold denial claim: "This wasn't made in Blender." with the tool name struck through in red |
| Structure | Hook → "everyone asks my secret" → prompt-only result (grey, flat, ugly) → "this is what you get with my X" (golden) → what X does (XP bar: camera / light / motion / sound) → "Every frame is code" → "Comment WORD" |
| Look | Golden hour: low sun through venetian blinds, hard stripe shadows, warm orange + deep red-brown, bloom, vignette, film grain, light chromatic aberration |
| Contrast beat | The "bad" version is the same set, desaturated, flat grey light, no shadows, music ducked |
| Captions | Inter ExtraBold, white, soft dark shadow, centered in the top third, max 2 lines, words pop in as spoken; key word in a yellow→green gradient; struck word gets a red bar |
| Screen | The monitor shows the story: title card, a retro "prompt — untitled.film" app with typing, an XP bar levelling up, LEVEL UP |
| Sound | Confident male VO (dry, compressed), lofi Rhodes chords + soft drums + vinyl crackle, ducked under the voice; whoosh on cuts, key clicks while typing, ticks on XP checks, boom on the hook and on the switch back to golden |
| End | 3D extruded orange word (the comment keyword) pops in front of the computer: "Comment / ROOM / and I'll send it to you" |

## Folder layout

```
code-cinema/
  SKILL.md            this file
  setup.sh            one-time install (Kokoro TTS + models, fonts)
  make.sh             script.json -> final.mp4 in one command
  engine/scene.html   three.js set, looks, SHOTS library, screen UI, captions, post FX
  engine/render.js    serves engine/ over http, captures frames -> video.mp4 (or previews)
  engine/lib/         vendored three.js r169 + addons + helvetiker font
  tools/tts.py        Kokoro voice per line -> s0.wav, s1.wav ...
  tools/build.py      script.json + wav durations -> timeline.json
  tools/sfx.py        synthesizes music.wav (lofi bed) + sfx.wav from the timeline
  tools/mix.py        voice + ducked music + sfx + video -> mp4
  projects/<name>/script.json   one folder per video
```

## Make a new video

1. `./setup.sh` once per fresh container.
2. Copy `projects/sample-every-frame` to `projects/<new-name>` and edit `script.json`.
3. Check framing fast: `python3 tools/tts.py P && python3 tools/build.py P && node engine/render.js P preview 1 4 8` (writes `P/preview_<t>.jpg`, ~2 s each).
4. Full build: `./make.sh projects/<new-name>` → `projects/<new-name>/final.mp4`. A 25 s video takes ~25-40 min on CPU (SwiftShader). For a faster draft set `"cfg": {"glScale": 0.66}` (3D renders smaller and is upscaled; captions stay sharp).

## script.json reference

```json
{
 "voice": "am_michael", "speed": 1.05,                  // any Kokoro voice; per-line "voice"/"speed" override
 "cfg": {"size": [1080,1920], "fps": 30, "note": "SKILL >\nPROMPT", "captionPos": "top",
         "captionSize": 0.068, "hl1": "#ffe34a", "hl2": "#7dff6a", "handheld": 1, "glScale": 1, "gap": 0.12, "blindTilt": 0.05},
 "music": {"bpm": 84, "gain": 1.0, "chords": [[53,57,60,64],[52,55,59,62],[50,53,57,60],[48,52,55,59]]},
 "segs": [ { "say": "spoken line", "text": "optional different caption", "shot": "screen_push",
             "look": "golden|flat", "screen": {...}, "hl": ["word"], "strike": ["word"],
             "cap": "top|center|bottom", "nocap": false, "gap": 0.12, "minDur": 0,
             "cta": "ROOM", "ctaTop": "Comment", "ctaBottom": "and I'll send it to you" } ]
}
```

- One seg = one spoken line = one shot. Keep lines to 3-10 words. `"shot": "same"` continues the previous camera move without a cut.
- `look` carries forward until changed. Use `flat` for exactly one short "prompt-only" beat.
- `screen` carries forward until the next seg that sets one.
- `hl` / `strike` match caption words ignoring case and punctuation.

### Shots (`engine/scene.html` → `SHOTS`)
`screen_push` (slow push on monitor) · `screen_full` (UI fills frame) · `low_hero` (low-angle slide) ·
`wide_window` (window, blinds, shafts) · `orbit_wide` (slow orbit) · `keyboard_slide` (macro across keys to the phone) ·
`mug_phone` · `pull_back` (screen → room reveal) · `top_down` · `cta` (end card). Add a shot as
`{a:[[camPos],[lookAt]], b:[[camPos],[lookAt]], fov}` or `{orbit:{c,r,h,a0,a1}, fov}`; units are metres, desk top is y=0.78, screen centre ≈ (0, 1.17, 0.11).

### Screens (`screen.type`)
- `title`: `text`, `strike` (red bar), `strikeAt` (s), `sub`, `size`, `color`
- `app`: `title`, `label`, `typed` (typed at `cps` from `typeAt`), `skill`, `click` (presses Generate, shows a render bar)
- `xp`: the app plus an XP panel: `role`, `from`, `to`, `max`, `checks` (ticked one by one)
- `levelup`: `text`
- `off`

## Writing a script in this style

Hook in the first 2 s, a claim that sounds impossible. Name the "bad" way, show it ugly for ~1.5 s,
then cut back to golden with a boom on the word "this". Explain the secret as a level-up of experience
(camera, light, motion, sound). One-line flex ("Every single frame is code."). End on a one-word
comment keyword so the CTA reads as a big 3D word. Keep the total 20-30 s.

## Changing the set

The whole room is procedural in `buildSet()`. Colours live in the `M` materials (desk `#6e2116`, beige `#e9dcc0`,
walls planked `#6b3a1e`). Sun angle: `sun.position` / `sun.target`; stripe thickness: `cfg.blindTilt`
(0 = thin bright stripes, 0.4+ = mostly closed). Swap or add props with the `box()` / `cyl()` helpers.
For a different room (studio, cafe, bedroom), copy `buildSet` and keep the same light rig: one hard sun through a
patterned occluder + warm practical lamp + dark hemisphere fill is what makes the look.

## Using this as a Claude skill

This folder is the skill. To add it to your Claude account, zip the `code-cinema` folder (SKILL.md at the top level)
and upload it in claude.ai under Settings → Capabilities → Skills. Claude will then follow this file whenever you ask
for "a code-cinema reel" or "a video like the Blender one".
