# Touchline

Turn full soccer recordings into goal reels with instrumental music.

**[Open Touchline](https://touchline-two-zeta.vercel.app)** · [Test results](docs/THREE_VIDEO_TESTS.md)

## Use

No sign-in needed. Everyone can watch all games and upload new recordings. The uploading browser controls edits and upload management.

1. Choose **New match** and upload a video (MP4, MOV, WebM or MKV; up to 16 GB and 120 minutes).
2. Keep the page open until upload finishes. Processing continues afterward.
3. Review detected moments, adjust clips and add any missed goals.
4. Save, regenerate and download your reel and music credits.

Automatic detection currently misses some goals and selects non-goals. Review is required. Clearing browser cookies resets editing access to your uploads.

## Development

Requires Node 22.13+, Python 3.12+ and FFmpeg.

```sh
npm ci
npm run dev
npm run build
node --experimental-strip-types --test tests/test-vercel-auth.mjs
```

Next.js runs on Vercel; AWS S3/DynamoDB store recordings and jobs; a separate Python/FFmpeg worker analyzes and renders them. See [deployment setup](docs/VERCEL.md).

Music: Hunted, Legionnaire (Original) and Titan by Scott Buckley, licensed CC BY 4.0. Include the downloaded credits when publishing. [Music licenses](docs/MUSIC_LICENSE.md).
