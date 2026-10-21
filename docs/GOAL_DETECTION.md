# Goal detection

Fixed indoor cameras with two recognizable red/orange portable nets now use a
ball-first pipeline before the general video scout:

1. Sample the recording and construct a median court view. Locate the portable
   goalposts, then verify that both proposed crops contain soccer goals. Physical
   occlusion is recorded; an invalid/moving/unsupported view uses the general scout.
2. Decode both goal regions at native detail, **6 frames/second over the entire
   recording**. RF-DETR Nano (ONNX, Apache 2.0) proposes small sports-ball objects.
   Object size relative to the net rejects foreground heads and feet. A single
   detection can propose a fast goal; there is no minimum dwell time or ten-goal cap.
3. Group ball sightings into short incidents. Opus 5.5 inspects full-court context
   and **2fps** context throughout each incident plus **8fps** goal close-ups around the strongest ball sighting, distinguishing the opening from side/rear net.
   Direct ball-in-net evidence is sufficient, including a ball that rebounds out;
   celebrations, a scoreboard and formal kickoffs are not required.
4. A separate, blinded Opus 5.5 request must confirm the same incident using a tighter goal crop and a different 5fps frame grid. These are two independent requests to the same model, not two different vision models.
   Both must report visible evidence, valid source timestamps, confidence >=0.6,
   and no uncertainty. Confidence is a model score, not calibrated accuracy.
   Only agreement becomes an automatically selected, verified goal. Disagreements
   and obscured outcomes remain unchecked; saves/misses are rejected.

Long incidents are split without dropping detections. Repeated views of the same
ball do not become extra goals. Goal count is never capped by a reel's target
length; thirty selected goals remain supported. Up to seventy uncertain moments
are retained separately, leaving editor capacity for thirty goals.

Each scan segment and review has a versioned S3 checkpoint. Revision/lease checks
protect concurrent edits/deletion; a retry resumes completed analysis. The worker
runs with two CPUs and 4GB RAM. Native-detail ball scanning can take longer than
real time; processing continues on AWS after the upload finishes.

The general camera path scans with Nova 2 Lite, then reviews candidates. An empty
scout receives a Sonnet frame pass over overlapping 24-second windows. It keeps
unconfirmed attempts unchecked. Neither path certifies all-goal recall when the
ball or goal line is hidden; zero detections is not proof of a scoreless match.

## Deploy and maintain

`main` deploys the web app, **not the AWS worker**. An AWS-authorized operator must
apply the narrowly scoped Bedrock grants in `worker/provision.py` to the existing
worker role (Sonnet 4.6 and US Opus 5.5 profiles/regional models), preserve the
pinned S3 detector asset, then run `python3 worker/deploy.py`. Do not rerun all
provisioning for a code update. Verify SSM success and worker health. Model source,
license, asset key and SHA-256 are in [MODEL_NOTICE.md](../worker/MODEL_NOTICE.md).
Never commit model binaries, recordings, credentials or owner cookies.

Contributors without AWS can run unit tests/builds. Mocked inference checks state
handling, not vision accuracy. Model/geometry changes require real positive and
negative clips before deployment. Increment `net_goals.VERSION` when changing
inference, sampling or checkpoint semantics; existing completed matches require
an explicit reanalysis revision to use a new pipeline.

`metrics.netAnalysisVersion`, `ballScanFPS`, `ballScanFrames`,
`ballScanCoverageSeconds`, `netCandidates`, `netVerifiedGoals` and `netModelUsage`
record the new path. `frameAnalysisVersion` identifies the general fallback.
Historical investigation results are in `MISSED_GOALS_6A5E_RESULTS.json`.
