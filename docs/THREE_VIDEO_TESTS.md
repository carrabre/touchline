# Three unique full-video tests

**Automatic all-goals detection: FAILED on two scoring matches.** The reviewed outputs include all source-audited goals, but they require human corrections. The third recording is a scoreless negative control and correctly produced no reel. These are three distinct recordings, not three soundtracks on one source.

## Sources and method

Belmont Media Center's publisher metadata identifies these three recordings as CC0 1.0. Source IDs, durations and SHA256 fingerprints are recorded in THREE_VIDEO_RESULTS.json. Publisher metadata is a rights assertion, not a separately negotiated release.

| Recording | Full duration | Full-source scout windows | Source goal count |
|---|---:|---:|---:|
| Boys vs Winchester, October 23, 2024 | 95:49 | 34 | 6 (4–2) |
| Girls vs Lexington, October 21, 2024 | 90:04 | 32 | 0 (0–0) |
| Boys vs Wilmington, October 1, 2024 | 86:42 | 31 | 4 (4–0) |

Every overlapping window used the production extraction method, Nova 2 Lite model and scout prompt, with two concurrent calls on the local host. Exact model responses were checkpointed into the production worker's durable namespace. No expected goal times or counts were provided to inference. Full source files were uploaded directly through the AWS SDK; this bypasses browser file upload. The deployed AWS worker independently reviewed candidates and rendered the actual reels. A refreshed AWS login with automatic credential renewal was needed after the initial long harness lost its session.

Reference counts use full-source score progression checks and consecutive source frames around each scoring sequence. Approximate goal seconds: Winchester 523, 982, 2366, 3372, 3663, 5053; Wilmington 853, 3077, 4059, 4954. They are audit reference times, not model predictions. They do not establish frame-perfect timing or benchmark accuracy on other footage.

## Raw automatic results and corrections

- **Winchester, original 64-second review:** 5 selected clips, 4 real goals, 2 missed goals and 1 false selection. Saved baseline retained locally.
- **Winchester, 96-second review:** recovered both missed goals, but selected 8 clips including 2 false moments (1040.7 and 4138.5 seconds). The final goal's model timestamp was 5072, about 19 seconds late; its original 5057–5092 trim missed the live goal around 5053. Six associations to scoring sequences do not equal six correctly timed automatic goal clips.
- **Winchester, reviewed result:** unchecked both false moments through the live Vercel studio, expanded the final clip start to 5033, disabled timestamp labels, and saved/regenerated. Six source goals are contained in six final clips. This is a manually reviewed output.
- **Lexington:** 32 scout windows returned no candidates. Worker ended at needs_review with zero events and no output MP4. The source stayed 0–0. No fake highlight was generated to fill an empty reel.
- **Wilmington:** five scout candidates were independently reviewed; only the fourth goal was retained. Three of four source goals were missed. A separate focused 64-second review of candidates 853, 3060 and 3091 also rejected them. A full original-window fallback review around the third goal returned false. That failed fallback experiment was removed from the production code.
- **Wilmington, reviewed result:** added the three missed goals at 14:13, 51:17 and 67:39 through the live studio, set 15-second pre-roll and 20-second post-roll, disabled timestamp labels, and saved/regenerated. Those events remain explicitly marked manual/Added by you. Four source goals are contained in four final clips. This is not an automatic four-goal success.

The worker now reviews 96 source seconds starting 60 seconds before each scout timestamp. Its review checkpoint namespace is versioned separately so older 64-second results cannot be silently reused. This fixes an observed context omission for Winchester; it does not solve model false positives or the Wilmington misses. All included goals still survive the target reel duration, and excluded clips remain excluded.

## Verification and limits

- Eleven media tests passed, including real FFmpeg rendering, slowed timestamp conversion, the wider context regression, included goals beyond the duration target, exclusions, duplicate merging, schema parsing, and music retry/regeneration.
- Live Vercel studio operations tested: exclude, trim, add missed events, save/regenerate. Source and reel browser readiness checked separately.
- Both complete MP4 decodes passed with H.264 video and AAC audio. Winchester is 234.094336 seconds with Titan; Wilmington is 140.085026 seconds with Hunted. Live browser sources and reels reached readyState 4 with no media errors. Exact output durations, song choices and source windows are recorded in THREE_VIDEO_RESULTS.json after export. Every audited goal lies inside a final rendered source window.
- Instrumental music is selected randomly from licensed Scott Buckley tracks, with the louder existing mix and downloadable attribution. Regeneration changes the previous random song. No YouTube audio was ripped.
- Browser file upload, interrupted upload, recording, two-hour processing, subjective audio listening and general automatic detection accuracy are not certified by these tests.
- No videos, signed object URLs, account owner IDs or credentials are committed to the public repository. Video outputs remain in the user's library and local task output folder.

Source: https://github.com/carrabre/touchline · App: https://touchline-two-zeta.vercel.app (no sign-in required; all games are publicly viewable).
