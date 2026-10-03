# Verification ledger

**Overall definition of done: NOT MET.** Additional full-video tests exposed automatic goal misses, false selections and a clipped live scoring moment. Reviewed reels can include all audited goals, but the automatic all-goals requirement is not met. Production browser file upload, recording and the 120-minute case remain unverified. See [three-video test report](THREE_VIDEO_TESTS.md) for the latest results; historical entries below describe their original runs.

## Assets prepared

- Source: **BHS Varsity Boys Soccer: Marauders vs Lexington 10/18/21**, Belmont Media Center, filmed at Harris Field, Belmont, MA. Archive source: https://archive.org/details/snafuinfinitysoccer-boys_101821-vs-lexington
- Usage basis: uploader's archive metadata explicitly marks it **Public Domain Mark 1.0**, http://creativecommons.org/publicdomain/mark/1.0/. Relevant metadata is preserved in `TEST_ASSET.json`. This records the publisher's rights assertion, not a separate independently negotiated release.
- Downloaded file: `soccer-boys_101821-vs-lexington.mp4`.
- FFprobe duration **5,441.387 seconds (90:41.387)**; size **527,784,221 bytes**; H.264 at **854 × 480** with AAC audio. Amateur school soccer from an elevated sideline; includes commentary, so it does not establish performance for silent stationary-camera footage.
- Maximum-length fixture constructed locally by repeating this authorized source and trimming at 120 minutes. FFprobe duration **7,200.096 seconds (120:00.096)**, size **698,723,511 bytes**. The second portion repeats earlier play; this is a container/duration stress fixture, not a new two-hour continuous game. **Not uploaded or processed in production.**

## Completed checks

- TypeScript compile: passed.
- Production web build: passed, including the final multipart/state pagination fixes.
- Python worker syntax: passed.
- React best-practices review: request/data access is server-side, large video uses file slices rather than full-file buffers, hook subscriptions clean up timers/listeners, controls have accessible names, responsive layout checked.
- AWS account/region, existing instance availability, SSM and Docker availability: verified before session expiry.
- Bedrock Nova Lite text invocation: passed before expiry. **This does not verify video analysis.**
- Dedicated storage/table/IAM setup calls reached access-key creation. A local bootstrap output-path error was fixed. Root session subsequently expired. Runtime credentials and worker were subsequently installed (see current setup).
- Clip duplicate/overlap and exclusion/budget unit checks: passed.
- Real local FFmpeg render: three tests passed in 7.238 seconds. Sample output is 22.042 seconds, 5,472,805 bytes, H.264 at 852 × 480 (display aspect ratio preserved) and AAC. Sample source windows: 60–72 seconds and 80–90 seconds, selected manually for render validation, not by the detector. A representative rendered frame was visually inspected; title and original timestamp labels are readable. Audio stream is present; subjective listening has not been certified.
- Local slow-video timestamp check: passed after correcting output duration when slowing the deep-review video.
- Local render initially failed because the Mac FFmpeg lacks `drawtext`. Overlays were replaced with generated text PNGs rather than depending on that optional filter.

Local rendering clips, when provided, are manually chosen smoke-test material, **not detected goals or highlights**. They are not proof that the autonomous detector works.

## Current setup

AWS authentication was restored on October 2. Scoped Site credentials are installed in environment revision 1; the worker is running on the existing instance. The unused setup access key was revoked. An initial Docker build could not reach HTTP package mirrors; switching Debian mirrors to HTTPS fixed it. Browser-assisted upload still fails while reading the selected local file, before match creation; native picker automation also timed out. This remains a browser upload verification blocker.

The Sites plugin's local helper directory also disappeared from the environment during this session. The build source and native hosting tools remain available; publishing uses a documented native source/version flow with manual source preparation where the helper is unavailable.

## Verified production web checks

- Private deployment succeeded at https://touchline-reels.carrabre.chatgpt.site on October 2, 2026.
- Sign in with ChatGPT completed with the existing account; live library and upload screens rendered.
- Anonymous API request: **HTTP 401**. Anonymous request carrying a forged authenticated-user header: **HTTP 401**. This verifies the outer sign-in gate, not all cross-user object ownership scenarios.
- Selected the full 90:41 source in the actual production file chooser. The app refused to upload because storage/processing credentials were unavailable and displayed the explicit AWS connection error. No source bytes were uploaded and no match job was created.
- Clicked the production recording control. It displayed the explicit offline recording error before requesting camera/microphone access. This is an unavailable-service check, not a successful recording test.
- Responsive production upload screen at **390 × 844**: DOM viewport and document widths both **390**, no horizontal overflow. Desktop and mobile screenshots saved in the task's outputs. Temporary viewport override restored.
- Production pipeline timings and detection quality remain unavailable. There is no production sample reel.

## Mandatory production matrix — all still outstanding unless specifically recorded below

| Requirement | Evidence/status |
|---|---|
| Upload full 90:41 source through production interface | Blocked by AWS connection |
| Close/reopen during background processing | Not tested |
| Actual visual event detection / source timestamp accuracy | Not tested; no measured misses/false positives |
| Preview, exclude, trim and add missed event | UI implemented; no production processing-backed test |
| Generate and regenerate music reel | No production output |
| Download and inspect MP4 playback/audio/completeness | No production output |
| 120-minute full pipeline | Fixture prepared locally; pipeline not tested |
| Interrupted upload recovery | Implemented; not production tested |
| Failed-job retry and saved checkpoint recovery | Implemented; not production tested |
| Duplicate submissions / render idempotency | Implemented conditional writes; not production tested |
| Invalid files | Input checks and ingestion rejection implemented; not production tested |
| Basic access controls | Anonymous and spoofed identity rejected (401); cross-user ownership and object URL checks remain untested |
| Browser recording | Incremental recording implemented; success and interruption paths unverified |
| Two-hour browser recording | Unverified; UI explains limitations |

To finish: restore authorized AWS access, provision scoped Site credentials, deploy the isolated worker, publish configuration, run this matrix through the live browser and retain model outputs, job timings and inspected source/reel timestamps. Correct issues and rerun affected tests before calling the app complete.

## October 2 follow-up checks

- Removed all privacy wording from the app interface and metadata, retaining existing access controls. Static rendered markup copy fell from 424 to 199 words (53%); this count excludes dynamic event evidence, errors and attributes.
- TypeScript and production build passed. Simplified UI deployed successfully with environment revision 1 and verified in the live signed-in browser.
- Three local media tests rerun: passed in 7.243 seconds, including real rendering and slow-video timestamp checks.
- Actual AWS worker render fixture: manually selected 0–12 seconds from the existing 22-second render smoke asset, analysis deliberately skipped. Worker completed in 7.69 seconds (render 7.38 seconds). Downloaded output: 12.019662 seconds, 2,830,679 bytes, H.264 852×480 + AAC. Full FFmpeg decode passed; a representative frame inspected. Artifact: outputs/aws-render-test.mp4 in the parent task outputs directory. This confirms deployed rendering/storage, not learned detection or the web upload path.
- Full 90:41 source uploaded using AWS CLI into a separate test namespace, then queued directly in DynamoDB. It reached video analysis. This bypasses the blocked browser upload path and cannot certify an end-to-end UI test.
- 120-minute fixture and full browser recording remain unverified.

- The first real video-analysis response included trailing JSON commentary, causing the strict parser to fail. Fixed parsing to read the first structured object and added a regression test. All four media tests passed in 7.242 seconds; the updated worker was installed and the test fixture requeued. Detection quality is still pending.

- Raw scout response used a bare event array instead of the requested wrapper. The parser now accepts both schemas, with regression coverage. The initial scout output also proposed implausible adjacent goals, so autonomous detection accuracy is expressly NOT certified; independent deep review and source inspection are required.

## All-goals correction

- Audited the entire 90:41 score progression at 30-second intervals, then inspected consecutive source frames around each scoring sequence. Final scoreboard: Belmont 1–2 Lexington. Three source goals at approximately 230, 2451 and 4929 seconds; no additional score increases. Ground truth and verification method are recorded in GOAL_AUDIT.json.
- Actual visual inference failed this audit: the scout hallucinated goals in ordinary footage, a separate video review misidentified the scoring team, and an image-sequence review incorrectly rejected a real goal. Automatic all-goal recall is NOT verified. The blind analysis run was stopped at needs_review; its checkpoints remain for diagnosis.
- Corrected two independent omission risks: every goal/possible-goal candidate is reviewed regardless of the optional-action review limit, and every included goal survives the selected reel-duration budget. Explicitly excluded goals remain excluded.
- Seven media tests passed in 7.300 seconds, including goals beyond a 90-second budget and 45 goal candidates beyond a 40-candidate limit.
- Queued an AWS worker render with all three source-audited goals and a 90-second target. This uses human-verified reference events and must not be represented as successful autonomous detection.

- The corrected AWS reel completed successfully: 101.063672 seconds, 24,064,360 bytes, worker 51.11 seconds (render 48.8). All 3 audited source goals fall within the 3 rendered clip windows; missing goals: 0. Entire downloaded MP4 decoded without errors. Representative output frames at 11, 39 and 76 seconds match the three scoring sequences. This is 3/3 audited inclusion, not 3/3 autonomous recall.
- Added an authenticated sample action that imports this fixed licensed fixture into the signed-in user's library, with its verified goal evidence. Edits generate that user's own subsequent reels; deleting the sample does not delete the shared fixture.

## Automatic goal detection — Nova 2 correction

- Replaced the failed Nova 1 visual detector with a goal-focused Nova 2 Lite scan and a separate review prompt. All goal candidates receive review; each review covers up to 64 source seconds slowed to half speed, so scout timestamp errors do not cut away the scoring action. New cache namespace prevents reuse of old-model detections.
- Full 90:41 source scanned in 33 overlapping windows. Scouting ran locally with ephemeral existing AWS authentication and two simultaneous model calls; exact model outputs were saved into the worker's durable checkpoint namespace. No expected goal times, counts or reference clips were supplied to inference. The AWS worker then independently reviewed all 6 candidates and rendered selected goals. This is a real full-source detection test, but not a browser-upload test or a production sequential-scout timing measurement.
- Result against independent source audit: **3 reference goals, 3 detected goals, 0 missed, 0 extra selected goals**. Review deduplicated the overlapping third-goal candidates and rejected the two late-game false candidates. Detected source seconds: 233.0, 2452.2, 4930.7; audited approximate seconds: 230, 2451, 4929. Maximum difference 3 seconds (matching tolerance 8 seconds). All true scoring moments are inside rendered windows.
- Automatically generated reel: **105.063672 seconds**, 24,527,107 bytes, 3 goal sequences, despite a 90-second target. Entire MP4 decoded without errors; output scoring frames at approximately 12, 48.8 and 83.3 seconds visually compared with source. Artifact: all-three-goals-automatic.mp4 in parent outputs.
- Measured model usage: **1,546,212 input / 1,054 output tokens**. Scout batch 358.90 seconds; worker candidate review/checkpoint traversal 60.00 seconds; render 50.77 seconds. Worker continuation 110.78 seconds. Upload, checkpoint transfer and local scouting run separately; no combined end-to-end UI timing is claimed. Billed charge not queried.
- Eight media tests passed in 7.370 seconds. TypeScript and web build passed. New model invocation is scoped to the existing worker role; no root credentials entered the worker or Site.
- Authenticated sample library entry uses the automatically detected reel, with its three events independently source-verified. Live browser loaded both source and reel without media errors and played the initial audited sample through its full duration; final automatic reel download/decode verified separately.
- This is one test match from an elevated school-game camera with commentary/score graphics. It does not prove perfect recall on all future sideline videos or two-hour matches.

## Three unique full recordings — October 2 follow-up

See [THREE_VIDEO_TESTS.md](THREE_VIDEO_TESTS.md). Full source scans covered 34, 32 and 31 overlapping windows. AWS review/rendering and production studio editing were exercised. Raw automatic outputs failed the all-goals requirement on Winchester and Wilmington. The scoreless Lexington recording produced no false goal reel. The final reels include manual corrections, which are explicitly recorded. Public GitHub source is connected to the protected Vercel deployment; successful Git-triggered deployment was verified.
