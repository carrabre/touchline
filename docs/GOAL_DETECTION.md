# Recovering empty goal scans

Touchline scans footage with Nova 2 Lite and independently reviews scoring candidates. A successful scan with no candidates does not establish that a game was scoreless: distant balls, small portable nets, obstructions and an unusual camera angle can defeat that video view.

An empty scout now triggers a separate Sonnet 4.6 frame pass. It examines overlapping 24-second windows, with up to twenty labeled source frames per window. A stationary indoor view can be focused on the playing area; moving/outdoor views retain the full frame. Crop geometry is validated and padded. Invalid geometry falls back to the full image.

Every nominated incident receives an independent review with up to forty detailed frames and absolute source timestamps. Only independently confirmed goals with confidence of at least 85% are selected automatically. Unconfirmed attempts stay available in the editor, unchecked, with the review explanation. They are not silently erased or represented as goals. The editor retains up to seventy optional uncertain attempts, leaving capacity for thirty goals; confirmed goals are never capped by this optional-candidate limit. The original video is preserved. This improves recovery and reviewability; it does not certify that all real goals can be recognized from every camera angle.

Analysis and reviews use versioned S3 checkpoints, bounded batches of three requests, and the existing revision/lease checks. Retries reuse completed work. The normal outdoor detector and reel selection rules remain compatible; confirmed goals still survive the reel duration target, including thirty goals.

## Deployment

Deploy the AWS worker as well as the Vercel frontend. The worker role needs `bedrock:InvokeModel` for the `us.anthropic.claude-sonnet-4-6` inference profile and its US regional foundation-model resources. These scoped grants are included in `worker/provision.py`; contributors can test and build without AWS access. Do not rerun all provisioning just to update code. An AWS-authorized operator should update the existing role's scoped model policy, then run `worker/deploy.py` and verify SSM success.

The detailed fallback adds model calls and processing time. Usage is included in `metrics.modelUsage`; `frameAnalysisVersion`, `frameModel` and `frameWindows` identify its use. Actual billed costs are not inferred from unit tests.

## Verification

The regression suite exercises source-clock timestamps, complete overlapping coverage, bad crop geometry, per-message image limits, empty-scout recovery, retained unchecked attempts and confirmed goals reaching rendering. Live inference also recognized a previously audited Winchester goal near source second 125 and rejected a separate saved/missed shot without inventing a goal.

The investigation of IMG_6349 and its final production result are recorded in `MISSED_GOALS_6A5E_RESULTS.json`. Model detections are separate from any independently supplied goal reference times; zero confirmed goals must not be reported as proof that none were scored.
