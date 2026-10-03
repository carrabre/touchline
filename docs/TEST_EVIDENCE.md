# Verification ledger

**Automatic all-goal detection is not reliable.** Review is required. Browser recording, interrupted uploads and the 120-minute pipeline remain unverified.

## Full-match analysis and rendering

- The original 90:41 Lexington match produced all three independently audited goals after the Nova 2 detector update.
- Three additional distinct recordings exposed missed goals, false selections and incorrect clip timing. Reviewed outputs included all ten audited goals after studio corrections. The scoreless control produced no reel.
- Both final scoring-match MP4s fully decoded without errors and loaded in the live browser.
- Eleven media checks passed, including real FFmpeg rendering, timestamp conversion, selection limits and music regeneration.

See [three-video report](THREE_VIDEO_TESTS.md), [structured results](THREE_VIDEO_RESULTS.json) and [original goal audit](GOAL_AUDIT.json).

## Public browser libraries

The app now uses signed browser sessions instead of a shared configured owner. New visitors need no sign-in and receive separate libraries. The existing owner's browser library was migrated before opening production access.

Session tests cover distinct identities, forged headers, tampered cookies, expired sessions and missing signing configuration. Production access and cross-library isolation are checked after deployment. These changes do not improve detector accuracy or certify the previously untested upload/recording paths.
