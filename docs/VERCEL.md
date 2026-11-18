# Deployment

Production: https://touchline-two-zeta.vercel.app
Source: https://github.com/carrabre/touchline

GitHub `main` automatically deploys to Vercel production. The app uses Next.js; build with `npm run build` (the Vercel build alias is `npm run build:vercel`).

Set server-only variables in Vercel:

- `SESSION_SECRET`: a random secret of at least 32 characters, consistent across deployments to preserve browser libraries.
- `MEDIA_ACCESS_KEY`, `MEDIA_SECRET_KEY`: scoped AWS credentials.
- `MEDIA_BUCKET`, `MATCH_TABLE`: existing S3 bucket and DynamoDB table.
- `REVIEWED_GOALS_ACCESS_SHA256`: server-only hash of the private goal tracker access key.

Production must be accessible without Vercel Authentication. Preview deployments can remain protected. Browser sessions use signed, HTTP-only cookies; each browser gets a random owner. Regular games and upload progress are publicly viewable. APIs check ownership for editing, deleting and managing uploads. Clearing cookies loses editing access; cross-device accounts are not implemented.

The private goal tracker at `/goals` reads the reviewed match from DynamoDB and signs its reel, portraits, and review clips from private S3 objects. Reviewed records use the `reviewed` stage and stay out of the public match library and media worker queue. Keep player IDs stable when editing credit, reusing the same ID when a player changes jerseys.

The existing media worker uses its instance IAM role. Update it with `python3 worker/deploy.py` and verify its deployment result. Do not commit secrets or recordings.

Before publishing, run the session tests and production build. Verify visitors see the same games and can view source videos/reels, while only uploaders can edit or manage their uploads.
