import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';

const COOKIE = 'touchline_session';
const LIFETIME = 365 * 24 * 60 * 60;
export function runtimeConfig(): Record<string, string | undefined> {
  return process.env;
}
function secret(): string {
  const value = process.env.SESSION_SECRET;
  if (!value || value.length < 32) throw new Error('Browser sessions are not configured.');
  return value;
}
function signature(payload: string): string {
  return createHmac('sha256', secret()).update(payload).digest('base64url');
}
/** A signed browser identity keeps visitors out of each other's libraries. */
export function requestOwner(request: Request): string | null {
  const token = request.headers.get('cookie')?.split(';').map(c => c.trim())
    .find(c => c.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1);
  if (!token || token.length > 600) return null;
  const [payload, supplied, extra] = token.split('.');
  if (!payload || !supplied || extra || !/^[A-Za-z0-9_-]+$/.test(payload)) return null;
  const expected = signature(payload);
  if (supplied.length !== expected.length || !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) return null;
  try {
    const { owner, expires } = JSON.parse(Buffer.from(payload, 'base64url').toString());
    const now = Math.floor(Date.now() / 1000);
    return typeof owner === 'string' && /^[A-Za-z0-9_-]{20,128}$/.test(owner)
      && Number.isSafeInteger(expires) && expires > now && expires <= now + LIFETIME + 60 ? owner : null;
  } catch { return null; }
}
export function createBrowserSession(request: Request): { owner: string; cookie: string } {
  const owner = randomBytes(32).toString('hex');
  const payload = Buffer.from(JSON.stringify({ owner, expires: Math.floor(Date.now() / 1000) + LIFETIME })).toString('base64url');
  const secure = new URL(request.url).protocol === 'https:' || process.env.NODE_ENV === 'production';
  return { owner, cookie: `${COOKIE}=${payload}.${signature(payload)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${LIFETIME}${secure ? '; Secure' : ''}` };
}
