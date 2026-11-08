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
3. **Pexels key:** https://www.pexels.com/api/   **Pixabay key:** https://pixabay.com/api/docs/  (both free)
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

- **Uploads from a new API project stay Private** until Google audits it. Make each video public in YouTube Studio,
  or apply for the free audit: https://support.google.com/youtube/contact/yt_api_form . Default privacy is `private` in `config.json`.
- **Free quota is 10,000 units a day.** An upload costs about 1,600 and each idea search 100, so a daily video fits easily.

## Settings (`config.json`, edit on github.com and commit)

- `niche`, `idea_queries`, `seed_ideas`: what to make.
- `voice.edge_voice`: any free Edge voice, e.g. `en-US-GuyNeural`, `en-GB-RyanNeural`, `en-US-ChristopherNeural`.
- `youtube.privacy`: `private`, `unlisted` or `public`.
- Change the daily time in the `cron` line of the workflow (UTC).
- Tip: watch a few videos before letting it upload publicly; YouTube can demonetize repetitive mass-produced AI content.
