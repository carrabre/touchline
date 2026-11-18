import { createReviewCookie, validAccessKey } from "@/lib/review-access";

export async function POST(request: Request) {
  const url = new URL(request.url);
  const origin = request.headers.get("origin");
  if (origin !== url.origin) return new Response(null, { status: 403 });
  const payload: unknown = await request.json().catch(() => null);
  if (!payload || typeof payload !== "object" || !("key" in payload) || !validAccessKey(payload.key)) {
    return Response.json({ error: "That access key did not match." }, { status: 403 });
  }
  const cookie = createReviewCookie(url.protocol === "https:" || process.env.NODE_ENV === "production");
  if (!cookie) return new Response(null, { status: 503 });
  return new Response(null, { status: 204, headers: { "Set-Cookie": cookie, "Cache-Control": "no-store" } });
}
