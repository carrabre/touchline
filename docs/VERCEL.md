# Deployment

Production: https://touchline-two-zeta.vercel.app
Source: https://github.com/carrabre/touchline

GitHub `main` automatically deploys to Vercel production. The app uses Next.js; build with `npm run build` (the Vercel build alias is `npm run build:vercel`).

Set server-only variables in Vercel:

- `SESSION_SECRET`: a random secret of at least 32 characters, consistent across deployments to preserve browser libraries.
- `MEDIA_ACCESS_KEY`, `MEDIA_SECRET_KEY`: scoped AWS credentials.
- `MEDIA_BUCKET`, `MATCH_TABLE`: existing S3 bucket and DynamoDB table.

Production must be accessible without Vercel Authentication. Preview deployments can remain protected. Browser sessions use signed, HTTP-only cookies; each browser gets a random owner. APIs check ownership before accessing recordings or changing matches. Clearing cookies loses access to that browser's library; cross-device accounts are not implemented.

The existing media worker uses its instance IAM role. Update it with `python3 worker/deploy.py` and verify its deployment result. Do not commit secrets or recordings.

Before publishing, run the session tests and production build. Verify an anonymous visitor can open the site and gets a separate library, and cannot read another owner's match.
