import "server-only";
import { signed } from "@/lib/aws";

const openRangeBytes = 8 * 1024 * 1024;
const responseHeaders = ["accept-ranges", "content-length", "content-range", "content-type", "etag", "last-modified"];

export async function mediaResponse(request: Request, key: string) {
  const range = request.headers.get("range");
  if (range && (range.length > 64 || !/^bytes=(?:\d+-\d*|-\d+)$/.test(range))) {
    return new Response(null, { status: 416 });
  }
  const openRange = range && /^bytes=(\d+)-$/.exec(range);
  const start = openRange ? Number(openRange[1]) : null;
  if (start !== null && (!Number.isSafeInteger(start) || !Number.isSafeInteger(start + openRangeBytes))) {
    return new Response(null, { status: 416 });
  }
  // Bounded streaming requests let the browser resume without a long-lived function.
  const upstreamRange = start === null ? range : `bytes=${start}-${start + openRangeBytes - 1}`;
  const headers = new Headers({
    "Cache-Control": "private, no-store",
    "Content-Disposition": "inline",
    "X-Content-Type-Options": "nosniff",
  });
  try {
    const method = request.method === "HEAD" ? "HEAD" : "GET";
    const upstream = await fetch(await signed(key, method), {
      method,
      headers: upstreamRange ? { Range: upstreamRange } : undefined,
      cache: "no-store",
      redirect: "error",
      signal: request.signal,
    });
    if (upstream.status === 416) {
      await upstream.body?.cancel();
      const contentRange = upstream.headers.get("content-range");
      if (contentRange) headers.set("Content-Range", contentRange);
      return new Response(null, { status: 416, headers });
    }
    if (!upstream.ok) {
      await upstream.body?.cancel();
      return new Response(null, { status: upstream.status === 404 ? 404 : 502, headers });
    }
    for (const name of responseHeaders) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return new Response(null, { status: 502, headers });
  }
}
