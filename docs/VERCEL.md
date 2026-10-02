Touchline supports both the original Sites runtime and Next.js on Vercel.

Vercel build: `npm run build:vercel`. The deployment uses existing AWS storage,
match records, and the isolated media worker. Set MEDIA_ACCESS_KEY,
MEDIA_SECRET_KEY, MEDIA_BUCKET, MATCH_TABLE and APP_OWNER_ID only as server
variables. Never commit their values.

This is a single-owner Vercel deployment. Vercel Authentication MUST protect
all deployments, including production domains (`ssoProtection.deploymentType:
all`). Everyone granted deployment access can access the owner's library.
Do not grant access or create sharing/bypass links for other users. Do not
disable protection. Multi-user public hosting needs application authentication
before changing these settings. The API ignores client-supplied Sites identity
headers on Vercel. The original Sites runtime retains its trusted gateway
identity through its Vite runtime alias.
