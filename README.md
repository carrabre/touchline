# Touchline

A private soccer match library, resumable uploader, incremental browser recorder, and highlight review studio. The intended production pipeline uses real visual analysis across the full match and a separate durable media worker.

Production web URL: https://touchline-reels.carrabre.chatgpt.site

**Current delivery state: incomplete.** The web app, scoped AWS storage connection and isolated worker are deployed. An actual AWS render/storage/download test passed. Full visual detection, browser upload and 120-minute processing remain unverified; see docs/TEST_EVIDENCE.md.

## Use

1. Sign in with ChatGPT at the private Site.
2. Choose New match, name the game, and select a supported video (MP4 recommended, MOV/WebM/MKV accepted). Maximum 16 GB and 120 minutes.
3. Keep the upload page open until transfer completes. Reselect the identical file to resume an interrupted multipart upload. Closing the page after upload does not cancel the durable job.
4. Return to the match to review clips. High confidence is a model judgment, not a certified goal. Preview each candidate, include/exclude it, change boundaries in seconds, or add a missed event with a source timestamp.
5. Save edits and regenerate, then download the MP4.

Processing requires the configured AWS media service.

## Architecture

- **Web**: React 19, Vinext/Next App Router, TypeScript, Sites/Cloudflare Workers. Owner-private Sign in with ChatGPT gate. Each API request also requires the trusted authenticated user ID; ownership is checked before file or match access. Same-origin mutation checks protect against cross-site submissions.
- **Storage**: a dedicated private S3 bucket `touchline-media-977099028101-us-east-1`, server-side AES256 encryption, public access blocked. Direct signed multipart uploads use 16 MB slices; the entire video never enters browser memory or a Worker request. Incomplete multipart uploads expire after seven days. Download/preview URLs are bearer capabilities expiring after one hour. Keep these URLs private.
- **State/queue**: dedicated DynamoDB table `touchline-matches`, on-demand billing. Conditional writes implement file submission idempotency, edit revisions and worker leases. Durable state is server-side. No browser storage is the source of truth.
- **Worker**: a separate Docker container on the existing AWS instance `i-0f165410a7653c04e`. Limits: 2 CPU, 4 GB RAM, 128 processes, one match at a time, no inbound listener or GPU access. Other services are preserved. Compute files are erased after each job; canonical files and analysis checkpoints persist in S3. The container restarts after host reboot.
- **Analysis**: Amazon Bedrock Nova Lite inspects overlapping 180-second video windows stepped by 170 seconds, covering the entire source at the model's 1 fps video sampling rate. Nova Pro independently reviews up to 40 candidate sequences at half speed (effective 2 fps in original time). Seconds are transformed back to source timestamps. Duplicate events are suppressed, overlapping clips merged, uncertain goals are candidates, not automatic goals. Checkpoints save each completed model call.
- **Editing/rendering**: FFmpeg, H.264/YUV420P + AAC, original aspect ratio, CRF20 once for clip editing, stream copy at final assembly. Clean cuts, title and optional source-time labels, original CC0 music, sidechain ducking beneath source audio, fast-start MP4. Short/default/long maximums are 90/180/240 seconds. Low-quality events are not added to fill time.

Convex was not used: the authorized AWS account already supports private large-file storage, atomic durable state, video inference and existing persistent compute. Keeping these together avoids another identity/storage bridge.

## Local development

Node >=22.13, Python 3.12+ and FFmpeg are required. No Docker is installed on the current Mac; the deployment target already has Docker.

```sh
npm ci
npm run dev
npx tsc --noEmit
npm run build
python3 -m venv .venv
.venv/bin/pip install -r worker/requirements.txt
SOCCER_SOURCE=/absolute/path/to/authorized.mp4 .venv/bin/python tests/test_media.py
```

The Sites starter supplies a mock identity in development only. Do not expose local development to the public network. Server configuration is through Worker environment bindings: `MEDIA_ACCESS_KEY`, `MEDIA_SECRET_KEY` (secrets), `MEDIA_BUCKET`, `MATCH_TABLE` (non-secret). The credential is restricted to this application's S3 bucket and DynamoDB table; never install root credentials into the Site.

## Finish infrastructure setup

After an authorized AWS session is available:

1. From this checkout run `python3 worker/provision.py`. This idempotently configures only dedicated Touchline storage/data resources and an additive scoped policy on the existing compute role. It stores the bootstrap key in the task's ignored `work/` directory with mode 0600. **An unused Touchline IAM access key was created before a local file-path error; revoke that unused key once the new working key is installed.** Do not rotate or touch unrelated users.
2. Set the four environment values in the Sites runtime, marking both credential values secret. Do not put secrets in `.openai/hosting.json` or Git.
3. Run `python3 worker/deploy.py`. Check its SSM command result and the isolated container logs. The container uses the instance IAM role rather than a stored AWS key. The host-network setting permits IMDSv2 access without weakening the host's metadata hop-limit; no application port is opened.
4. Republish the same Site after runtime configuration. Do not create another Site or overwrite another deployment.
5. Execute the complete production matrix in `docs/TEST_EVIDENCE.md`. The definition of done remains unmet until both required long-form production runs pass.

## Reliability and limits

- MIME declarations are validated before upload; FFprobe validates real media, duration and resolution at ingestion. Invalid bytes can be uploaded but must become a failed job, not a reel.
- At most three active submissions per owner and one worker job run concurrently. Filename/size/mtime plus first/last MB content fingerprint deduplicates repeated UI submissions. This is a resumability identity, not a whole-file cryptographic integrity guarantee.
- Jobs acquire a 30-minute renewable lease. Each segment/candidate saves progress. SDK network retries precede up to three job attempts, after which a visible failure offers retry. Multiple workers cannot publish the same revision through the lease check. Render output keys include edit revision.
- Original footage remains stored until the match is discarded. Discarded objects are removed by the worker; multipart cleanup also has a lifecycle safety net. Retention policies and cost alarms should be reviewed before large-scale use.
- Source footage is sent to Amazon Bedrock for inference. No uploaded footage is public by default.
- 1 fps scouting can miss brief ball trajectories. Distant stationary footage, occlusion, poor lighting and small goals require careful review. Detection performance has **not** been measured; no accuracy claim is made.
- Browser recording saves five-second segments and stops rather than allowing an unbounded upload backlog. Interruptions preserve acknowledged segments. Backgrounding/locking mobile browsers can suspend capture. Neither short successful recording nor two-hour recording has been verified yet.
- A single existing host is a single point of compute availability. Queued/checkpointed work survives a host outage, but waits for recovery. Automatic analysis is visual only at present; game audio is retained and mixed but is not currently an analysis signal.

See `docs/TEST_EVIDENCE.md`, `docs/COSTS.md`, and `docs/MUSIC_LICENSE.md` for evidence and assumptions.
