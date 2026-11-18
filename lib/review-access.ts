import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const REVIEW_COOKIE = "touchline_review";
const lifetime = 90 * 24 * 60 * 60;

function equal(a: string, b: string) {
  return a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export function validAccessKey(key: unknown) {
  const expected = process.env.REVIEWED_GOALS_ACCESS_SHA256;
  return typeof key === "string" && /^[a-zA-Z0-9_-]{40,90}$/.test(key)
    && !!expected && /^[a-f0-9]{64}$/.test(expected)
    && equal(createHash("sha256").update(key).digest("hex"), expected);
}

function signature(expires: string) {
  const secret = process.env.SESSION_SECRET;
  const accessHash = process.env.REVIEWED_GOALS_ACCESS_SHA256;
  if (!secret || secret.length < 32 || !accessHash) return null;
  return createHmac("sha256", secret).update(`private-goals:${accessHash}:${expires}`).digest("hex");
}

export function hasReviewAccess(cookie: string | undefined) {
  if (!cookie || !/^\d{10}\.[a-f0-9]{64}$/.test(cookie)) return false;
  const [expires, supplied] = cookie.split(".");
  const now = Math.floor(Date.now() / 1000);
  if (Number(expires) <= now || Number(expires) > now + lifetime + 60) return false;
  const expected = signature(expires);
  return !!expected && equal(supplied, expected);
}

export function createReviewCookie(secure: boolean) {
  const expires = String(Math.floor(Date.now() / 1000) + lifetime);
  const sig = signature(expires);
  if (!sig) return null;
  return `${REVIEW_COOKIE}=${expires}.${sig}; Path=/goals; HttpOnly; SameSite=Lax; Max-Age=${lifetime}${secure ? "; Secure" : ""}`;
}
