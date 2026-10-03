# Verification ledger

**Automatic all-goal detection is not reliable.** Review is required. Browser recording, interrupted uploads and the 120-minute pipeline remain unverified.

## Full-match analysis and rendering

- The original 90:41 Lexington match produced all three independently audited goals after the Nova 2 detector update.
- Three additional distinct recordings exposed missed goals, false selections and incorrect clip timing. Reviewed outputs included all ten audited goals after studio corrections. The scoreless control produced no reel.
- Both final scoring-match MP4s fully decoded without errors and loaded in the live browser.
- Eleven media checks passed, including real FFmpeg rendering, timestamp conversion, selection limits and music regeneration.

See [three-video report](THREE_VIDEO_TESTS.md), [structured results](THREE_VIDEO_RESULTS.json) and [original goal audit](GOAL_AUDIT.json).

## Shared game library

The site now lists games and upload progress globally. Anyone can watch and download recordings/reels. Upload management, editing, retries and deletion remain limited to the uploading browser. Internal validation fixtures and discarded jobs are hidden. The previous isolated-library checks describe the earlier release; the latest shared-access checks are recorded in [PUBLIC_ACCESS_TESTS.json](PUBLIC_ACCESS_TESTS.json).

Seven session/access tests pass. Production verification covers shared listing, public previews, upload visibility, uploader-only management, and desktop/mobile button spacing. Detector accuracy and the previously untested long recording/upload paths remain unchanged.
