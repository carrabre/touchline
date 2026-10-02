# Verification ledger

**Definition of done: NOT MET.** No end-to-end production soccer reel exists. This ledger distinguishes completed local checks from blocked production tests.

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
- Dedicated storage/table/IAM setup calls reached access-key creation. A local bootstrap output-path error was fixed. Root session subsequently expired. Runtime credentials and worker are **not installed**.
- Clip duplicate/overlap and exclusion/budget unit checks: passed.
- Real local FFmpeg render: three tests passed in 7.238 seconds. Sample output is 22.042 seconds, 5,472,805 bytes, H.264 at 852 × 480 (display aspect ratio preserved) and AAC. Sample source windows: 60–72 seconds and 80–90 seconds, selected manually for render validation, not by the detector. A representative rendered frame was visually inspected; title and original timestamp labels are readable. Audio stream is present; subjective listening has not been certified.
- Local slow-video timestamp check: passed after correcting output duration when slowing the deep-review video.
- Local render initially failed because the Mac FFmpeg lacks `drawtext`. Overlays were replaced with generated text PNGs rather than depending on that optional filter.

Local rendering clips, when provided, are manually chosen smoke-test material, **not detected goals or highlights**. They are not proof that the autonomous detector works.

## Blocker

AWS CLI root login session expired. Existing browser sign-in renewal required a CAPTCHA. It cannot be completed autonomously. No root credentials were put into the Site or repository. A dedicated unused IAM access key created before the local path error should be revoked once setup resumes. The private web surface explicitly shows media processing offline until its scoped credentials are configured.

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
