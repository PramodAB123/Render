# Free automated video pipeline (runs in the cloud on GitHub Actions)

Nothing runs on your PC. GitHub's free cloud runners do every step, every day at 7 PM India time,
or whenever you press **Run workflow**:

```
YouTube Data API (trending ideas) -> Ollama llama3.2:3b on the runner (script) -> Edge-TTS voice
-> Pexels + Pixabay stock clips  OR  code-cinema 3D room (every frame rendered in code)
-> synthesized lofi bed or your free music -> FFmpeg captions + mix -> thumbnail -> YouTube upload
```

The workflow is `.github/workflows/make-video.yml`. Every finished video is also saved on the run's page
(Artifacts > "video") for 14 days, so you can watch it before making it public.

**Cost: free.** A private repo gets 2,000 free Actions minutes a month; a stock video takes about 6-10 minutes,
a 3D cinema video about 20-30. A public repo has unlimited minutes (your keys stay hidden in Secrets either way).

## Your checklist

1. **Push this folder to GitHub.** It is already linked to `github.com/PramodAB123/Render`.
   Create that repo on github.com if it doesn't exist (private is fine), then push (see the reply in the thread).
2. **Google Cloud project (free):** https://console.cloud.google.com/
   1. Create a project, then APIs & Services > Library > enable **YouTube Data API v3**.
   2. Credentials > Create credentials > **API key** (for trending ideas).
   3. OAuth consent screen: External, your app name + email, add yourself as a test user, then **Publish app**.
   4. Get the upload refresh token in your browser: follow `YOUTUBE_TOKEN.md` (uses Google's OAuth Playground, about 5 minutes).
3. **Pixabay key:** https://pixabay.com/api/docs/ (free). **Pexels key** is optional: Pexels paused new API keys
   (Nov 2026). Leave `PEXELS_API_KEY` unset and the pipeline uses Pixabay only; add it later if Pexels reopens.
4. **Add GitHub Secrets:** repo > Settings > Secrets and variables > Actions > New repository secret:

   | Secret | Value |
   |---|---|
   | `YOUTUBE_API_KEY` | the API key from step 2.2 |
   | `PEXELS_API_KEY` | Pexels key |
   | `PIXABAY_API_KEY` | Pixabay key |
   | `YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` | from `YOUTUBE_TOKEN.md` |

5. **First test:** repo > Actions > "Make video" > Run workflow (untick Upload for a dry run). Download the video from the run page.
6. **Verify your channel's phone number** at https://www.youtube.com/verify so custom thumbnails are allowed.
7. **Optional music:** commit free tracks (YouTube Audio Library, "no attribution required") into `music/`.

### YouTube API limits

- **No billing, no paid tier.** Google does not sell YouTube API quota. Default: 10,000 units/day, plus up to
  100 uploads and 100 searches a day (1 unit each); a custom thumbnail costs 50. One video a day uses well under 100 units.
- Uploads go out as `private` by default (`config.json` > `youtube.privacy`) so you can check them first; set it to `public` when you trust it.
- Pexels and Pixabay ask you to credit the creators: the pipeline adds a "Footage:" credits line to each description automatically.

## Length and visuals

**Length** and **orientation** are separate choices in the Run workflow form, for every mode.
- Length: `30 sec`, `1 min`, `3 min`, `5 min`, `10 min`. 1 min and longer are written by Ollama in chapters
  (outline first, then each chapter).
- Orientation: `portrait` (9:16, Shorts/Reels; up to 3 min it uploads as a Short with #shorts) or `landscape`
  (16:9 normal YouTube video, subtitles at the bottom, no #shorts tag). The 3D `cinema` room is portrait-only, up to 1 min.

**Visuals:**
- `stock`: Pixabay (and Pexels if you have a key) clips.
- `ai`: every scene is an AI image, generated free on the runner's CPU, with slow zoom/pan (Ken Burns) motion.
- `mix`: AI image and stock clip alternate (best balance of realism and speed).
- `doc`: documentary look. Chapter openings and every other scene are AI stills with slow camera moves, the rest are
  Pixabay clips (slowed slightly); crossfades between scenes, fade-through-black + "CHAPTER N" title cards, cinematic
  black bars, narrator tone, and sound design (whoosh on cuts, low boom on chapters, quiet drone). Best with `history`,
  `mystery` or `horror` and 3-10 min. At most 12 AI images per video.
- `2d`: animated cartoon story, always vertical (Short = ~55 s; 1/3 min also vertical). Original flat-vector characters
  (with optional pet) that blink, talk and react (scared/happy/angry/sad), parallax backgrounds (road, forest, mountains,
  snow, city, cabin, house, vehicle, sea, desert, cave, space, school), weather (snow, blizzard, rain, storm, fog),
  a HUD bar with clock/day/temperature/location, PART tag, route maps, checklists, radio messages, fact chips, big
  stats, pop-in captions with red keywords, and a two-button "vote in the comments" end card. Narrator uses the genre
  voice; every character gets its own free Edge voice, and each line's emotion changes speed and pitch. All drawn in
  code by `toon/toon.html` (about 3 minutes of rendering per minute of video), no AI images needed.
  Motion is driven by **GSAP** (free "no charge" license, installed from npm): one master timeline per video with
  expo/back/elastic easing for camera punch-ins and drift, squash-and-stretch character entrances, wipe / zoom /
  slide / iris scene transitions, spring-in captions with a camera shake on keywords, staggered chips and checklist
  ticks, a self-drawing map route with a bouncing pin, typed radio messages and elastic vote buttons. The timeline
  is paused and seeked to each frame's time, so renders are frame-exact.
  It follows the rules of the MIT-licensed **claude-animation-skills** repo (stick-figure + graph skills), which the
  workflow checks out at a pinned commit for its fonts: captions of 1-2 words timed to the voice word by word
  (Edge-TTS word timings, no extra model), whip transitions with motion blur, impacts (burst + shake + flash) on
  keywords, constant handheld drift, HUD and text kept inside the Instagram/Shorts safe area, a self-drawing line
  graph shot, and pacing of about 2.75 words per second.
- **Length fitting (all modes except cinema):** after the voice is made, the narration is brought close to the
  length you picked: sped up together (up to 1.25x, pitch kept) if too long, or given longer pauses if too short.
- Every video folder also gets `sheet.jpg`, an 8-frame contact sheet with the safe area marked in red, for a quick check.
- `stick`: stick-figure explainer/story made with the **stick-figure engine of claude-animation-skills** (its rig,
  faces, poses, props, whip transitions with motion blur, lowercase 1-2 word Poppins captions, grade). The original
  needs shots written by hand; `stick/auto_shots.js` builds them from the script automatically using 12 setups:
  closeup, talk, walk, run, crowd, object (labelled crate), reveal (chest opens), night (lantern), impact (burst),
  sea (ship), bigtext, think. Script follows the skill: hook in action, the belief, a turn on "But", examples,
  the mechanism, the payoff. Landscape puts the 9:16 frame on a blurred widened copy.
- `cinema`: the 3D code-rendered room (Shorts only).

**AI images**: model `Lykon/dreamshaper-8-lcm` (Stable Diffusion 1.5 fine-tune), license CreativeML OpenRAIL-M, which
allows commercial use of the images but forbids harmful/illegal uses. No API, no key, no account; it runs on GitHub's runner.
About 10-25 s per image. If an image fails, that scene falls back to a stock clip. Change `image` in `config.json` to tune steps/size.

**Rough run times** (GitHub free runner): Short ~8-10 min; 5-min `mix` ~25-35 min; 5-min `ai` ~35-45 min; 10-min `ai` ~60-80 min.
Private repo: 2,000 free minutes/month, then runs are blocked (never billed without a card). Public repo: unlimited.

## Genres

Pick one in the **Genre** dropdown when you press Run workflow. Daily automatic runs rotate through all five.

| Genre | Script | Clips | Look | Voice | Music | Pace |
|---|---|---|---|---|---|---|
| horror | slow-burn dread, cliffhanger | dark, foggy, abandoned, night | dark, desaturated, blue shadows, grain, vignette | deep slow male + echo | slow 60 bpm diminished chords | long pauses |
| comedy | relatable, punchlines, twist ending | funny animals, faces, fails | bright, punchy colour | upbeat fast female | bouncy 116 bpm major | snappy |
| science | true facts building to a wow | space, lab, nature | clean, crisp, cool tint | clear British male | curious 92 bpm | medium |
| motivation | punchy speech, rising energy | training, running, sunrise | high contrast, warm | deep steady male | driving 96 bpm | dramatic pauses |
| mystery | documentary clues, open question | fog, ocean, old maps, ruins | muted, purple-blue | calm narrator | eerie 70 bpm | measured |

Each genre lives under `genres` in `config.json`: edit its `tone`, `seed_ideas`, `idea_queries`, `visual_hint`, `grade` (FFmpeg colour filter),
`voice` (any free Edge voice + rate/pitch), `music` (bpm + chords), `gap` (pause between lines), caption `highlight` colour, `cta`, `tags`.
To use real free music for a genre, add tracks to `music/<genre>/` (e.g. `music/comedy/`).

## Settings (`config.json`, edit on github.com and commit)

- `default_genre`, `daily_genre` (`rotate` or one genre name).
- `youtube.privacy`: `private`, `unlisted` or `public`.
- Change the daily time in the `cron` line of the workflow (UTC).
- Tip: watch a few videos before letting it upload publicly; YouTube can demonetize repetitive mass-produced AI content.
