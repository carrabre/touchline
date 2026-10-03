# Touchline

Turn soccer recordings into goal reels with instrumental music.

**[Open app](https://touchline-two-zeta.vercel.app)** · [Three-video results](docs/THREE_VIDEO_TESTS.md) · [30-goal test](docs/THIRTY_GOAL_TEST.md)

## Use

Everyone can watch all games and upload recordings without signing in. Only the uploading browser can edit or delete its games; clearing cookies loses those permissions.

1. Choose **New match** (MP4, MOV, WebM or MKV; up to 16 GB / 2 hours). Keep the page open until uploading finishes.
2. Review moments, trim clips, add missed goals, then regenerate and download.
3. **Delete** on a library card or **Delete video** in the studio removes the game, source and reel from the shared library. Confirm before deleting; there is no restore. Processing jobs can also be deleted. AWS media cleanup follows asynchronously.

Reels support at least **30 selected goals**, including manually added goals. Goals and manual moments are retained even when they exceed the 90-second / 3-minute / 4-minute target; that target limits optional other highlights. The editor accepts up to 100 moments. Automatic detection can miss goals or select non-goals, so review is still required. The 30-clip capacity test uses generated footage; it does not measure detection accuracy.

## Contribute without AWS access

Clone this repo, make a branch and submit a pull request. You do not need AWS credentials to build or run the tests. Node 22.13+, Python 3.12+ and FFmpeg are required.

```sh
npm ci
python3 -m venv .venv
.venv/bin/pip install -r worker/requirements.txt
node --experimental-strip-types --test tests/*.mjs
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
npm run build
npm run dev
```

Without server secrets, local development shows an empty library and “Processing unavailable”; real uploads require the configured deployment. Tests use local fixtures and dummy credentials. GitHub Actions runs tests and the build without AWS access.

Change `app/page.tsx` / `app/globals.css` for UI, `app/api/` / `lib/` for web APIs, and `worker/` for detection/rendering. Keep the shared `Match` / `Event` contract in `lib/aws.ts` compatible with existing stored jobs: add optional fields with defaults, preserve IDs, statuses, timestamps, storage paths and revision/lease checks. Update both API and worker when changing that contract, and add a regression test. Preserve server-side uploader checks; the browser's `canEdit` flag only controls presentation.

## Deploy from GitHub

`main` automatically deploys the **web app to Vercel**. It does **not** update the AWS worker. Contributors should wait for green checks and have the owner review changes before merging. These checks are not a configured branch-protection gate.

For worker changes, the AWS-authorized owner pulls the tested `main` commit and runs `python3 worker/deploy.py` with the AWS CLI already signed in. Check the returned SSM command succeeds and the container stays running, then test an upload/regeneration on the live app. Deploy backward-compatible worker changes before web changes that depend on them. Avoid deploying while jobs are processing: the script restarts the worker. Keep the previous Git commit available for rollback (Vercel rollback for web; rerun the worker deploy script from that commit for AWS).

Keep `SESSION_SECRET` stable across web deployments and keep AWS variables server-only. Never commit credentials, `.env` files or recordings. Deployment settings and variables: [setup](docs/VERCEL.md).

Music: Hunted, Legionnaire (Original) and Titan by Scott Buckley, CC BY 4.0. Include the downloaded credits when publishing. [Licenses](docs/MUSIC_LICENSE.md).
