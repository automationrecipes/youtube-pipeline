# Automation Recipes — hands-free YouTube pipeline

Every day GitHub Actions does all of this on its own, using free tools only:

| Step | Tool (free) |
|---|---|
| Topic + script + title/description/tags | Google Gemini API (free tier) |
| Voiceover | edge-tts (Microsoft neural voices) |
| B-roll footage | Pexels API |
| Captions, editing, logo watermark | ffmpeg |
| Thumbnail (frame + text + AI avatar) | Pillow |
| Upload + thumbnail | YouTube Data API |
| Scheduler | GitHub Actions cron |

Schedule: one long video at 13:37 UTC and one Short at 17:13 UTC each day (edit `.github/workflows/daily.yml`).

## One-time setup

1. **Create a GitHub repo** (Public = unlimited free Actions minutes; Private = 2,000 min/month, enough for ~1 video/day). Upload everything in this folder.
2. **Add secrets** — repo → Settings → Secrets and variables → Actions → *New repository secret*:
   - `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` — from `youtube_token.json`
   - `GEMINI_API_KEY` — https://aistudio.google.com/apikey
   - `PEXELS_API_KEY` — https://www.pexels.com/api/
3. **Optional variables** (same page, *Variables* tab): `PRIVACY` (`private` / `public`), `TTS_VOICE`, `ENABLE_SHORTS` (`0` to turn Shorts off).
4. **Optional branding** in `assets/`: `logo.png` (watermark), `avatar.png` (transparent PNG of the AI host for thumbnails), `music.mp3` (royalty-free background track, e.g. from YouTube Audio Library).
5. **Test**: Actions tab → *Daily video* → *Run workflow* with `dry_run = 1`. Download the result from the run's Artifacts and check it. Then run once with `dry_run = 0`.

## Important YouTube limits

- **Uploads stay private until your API project passes Google's free YouTube API audit.** Videos uploaded by unverified API projects are locked to private. Apply here: https://support.google.com/youtube/contact/yt_api_form (choose the audit / quota extension form). Once approved, set the `PRIVACY` variable to `public`.
- **Custom thumbnails** need a phone-verified channel: https://www.youtube.com/verify
- Default API quota (10,000 units/day) covers about 6 uploads a day.
- The pipeline marks every video as containing AI-generated (synthetic) content.
