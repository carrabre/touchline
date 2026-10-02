/** Vercel uses server-only environment variables and deployment authentication. */
export function runtimeConfig(): Record<string, string | undefined> {
  return process.env;
}
export function requestOwner(_request: Request): string | null {
  // This single-owner deployment must have Vercel Authentication on ALL URLs.
  // Never trust the Sites identity header on a public Node deployment.
  return process.env.VERCEL === '1' ? process.env.APP_OWNER_ID || null : null;
}
