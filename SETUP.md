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

**Length** (Run workflow form): `short` = vertical Short (~30 s). `1 / 3 / 5 / 10 min` = 16:9 narrated video with chapters,
written by Ollama in parts (outline first, then each chapter), subtitles at the bottom, no #shorts tag.

**Visuals:**
- `stock`: Pixabay (and Pexels if you have a key) clips.
- `ai`: every scene is an AI image, generated free on the runner's CPU, with slow zoom/pan (Ken Burns) motion.
- `mix`: AI image and stock clip alternate (best balance of realism and speed).
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
